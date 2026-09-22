import * as z from "@zod/zod";
import { Console, Effect, Option } from "effect";
import { Addon, digestToSRI, fetch, hash, parseJSON, parseSchema, response, toSRI, tupleOf } from "./util.ts";

// Mozilla addons server

const AddonServerFile = z.object({
  is_webextension: z.literal(true),
  url: z.url(),
  hash: z.templateLiteral(["sha256:", z.hash("sha256")]),
});

const AddonServerResponse = z.object({
  current_version: z.object({
    version: z.string(),
    files: tupleOf([AddonServerFile]),
  }),
});

const SERVERS = {
  firefox: "https://addons.mozilla.org/api",
  thunderbird: "https://addons.thunderbird.net/api",
} as const;

export const fetchAMO = (server: keyof typeof SERVERS, id: string) =>
  fetch(`${SERVERS[server]}/v4/addons/addon/${id}/`).pipe(
    Effect.andThen(response.ok),
    Effect.andThen(response.text),
    Effect.andThen(parseJSON),
    Effect.andThen(parseSchema(AddonServerResponse)),
    Effect.map(({ current_version: data }) => ({
      version: data.version,
      file: {
        url: data.files[0].url,
        hash: digestToSRI(data.files[0].hash),
      },
      passthru: { id },
    } as Addon)),
    Effect.retry({ times: 2 }),
    Effect.result,
  );

// Mozilla 3rd-party/self-hosted

const Manifest = z.object({
  addons: z.record(
    z.string(),
    z.object({
      updates: z.array(z.object({
        version: z.string(),
        update_link: z.url(),
        update_hash: z.templateLiteral(["sha256:", z.hash("sha256")]).optional().transform(Option.fromUndefinedOr),
      })).nonempty(),
    }),
  ),
});

export const fetchMozilla = (url: string) =>
  fetch(url).pipe(
    Effect.andThen(response.ok),
    Effect.andThen(response.text),
    Effect.andThen(parseJSON),
    Effect.andThen(parseSchema(Manifest)),
    Effect.map((data) =>
      Object.entries(data.addons).map(([id, { updates }]) => ({
        id,
        version: updates.at(-1)!.version,
        url: updates.at(-1)!.update_link,
        hash: updates.at(-1)!.update_hash,
      }))
    ),
    Effect.andThen((addons) =>
      Effect.forEach(addons, (addon) =>
        Option.match(addon.hash, {
          onSome: (hash) =>
            Effect.succeed({
              version: addon.version,
              file: {
                url: addon.url,
                hash: digestToSRI(hash),
              },
              passthru: { id: addon.id },
            } as Addon),
          onNone: () =>
            fetch(addon.url).pipe(
              Effect.tap(Console.log(`Downloading ${addon.url} to hash it`)),
              Effect.andThen(response.ok),
              Effect.andThen(response.arrayBuffer),
              Effect.andThen(hash("SHA-256")),
              Effect.map(toSRI("sha256")),
              Effect.map((hash) => ({
                version: addon.version,
                file: {
                  url: addon.url,
                  hash,
                },
                passthru: { id: addon.id },
              } as Addon)),
              Effect.retry({ times: 2 }),
            ),
        }).pipe(
          Effect.result,
          Effect.map((result) => ([addon.id, result] as const)),
        ), { concurrency: 3 })
    ),
    Effect.map((items) => Object.fromEntries(items)),
    Effect.result,
  );
