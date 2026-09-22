import "@zod/zod/compile";
import { Console, Effect, FileSystem, Path, Result } from "effect";
import { Command, Argument, Flag } from "effect/unstable/cli";
import { NodeServices } from "@effect/platform-node";

import addons from "./addons.ts";
import { Addon, parseJSON } from "./util.ts";

const command = Command.make("nix-browser-addons-generator", {
  output: Argument.Path("output", { pathType: "directory" }),
  concurrency: Flag.Int("concurrency").pipe(Flag.withDefault(10)),
}, ({ output, concurrency }) => Effect.gen(function*() {
  const fs = yield* FileSystem.FileSystem;
  const path = yield* Path.Path;

  yield* Console.info(`Saving output to ${output}`);
  yield* fs.makeDirectory(output, { recursive: true });

  const products = Object.fromEntries(
    Object.entries(addons).map(([k, v]) => [k, Effect.all(v, { concurrency })])
  );

  const data = yield* Effect.all(products, { concurrency: "unbounded" });

  for (const [product, addons] of Object.entries(data)) {
    yield* Console.log(`=== ${product} ===`);
    const file = path.join(output, `${product}.json`);
    const base = yield* Effect.orElseSucceed(
      fs.readFileString(file).pipe(Effect.andThen(parseJSON)),
      () => ({}),
    );

    const goodAddons: [string, Addon][] = [];

    for (const [slug, result] of Object.entries(addons)) {
      yield* Result.match(result, {
        onSuccess: function*(addon) {
          yield* Console.log(`- ${slug}: OK (${addon.version})`)
          goodAddons.push([slug, addon]);
        },
        onFailure: function*(error) {
          yield* Console.error(`- ${slug}: FAIL ${error})`);
        },
      });
    }

    const finalAddons = { ...base, ...Object.fromEntries(goodAddons) };
    yield* fs.writeFileString(file, JSON.stringify(finalAddons));
  }
}));

await Effect.runPromise(
  Command.runWith(command, { version: "1.0.0" })(Deno.args).pipe(Effect.provide(NodeServices.layer))
);
