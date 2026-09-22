import * as z from "@zod/zod";
import { Console, Effect, Exit, Request, RequestResolver } from "effect";
import { decodeHex } from "@std/encoding";
import { Addon, fetch, hash, listOf, parseJSON, parseSchema, parseXML, response, toSRI, tupleOf } from "./util.ts";

const AppId = z.string().regex(/^[a-p]{32}$/).length(32);
export type AppId = z.infer<typeof AppId>;

// Omaha v4

const OMAHA_URL = "https://update.googleapis.com/service/update2/json";
const CHROME_VERSION = "140.0.0.0";

const PipelineOperationDownload = z.object({
  type: z.literal("download"),
  out: z.object({ sha256: z.hash("sha256") }),
  urls: z.array(z.object({ url: z.url() })).nonempty(),
  size: z.number(),
});

const PipelineOperationCrx3 = z.object({
  type: z.literal("crx3"),
  in: z.object({ sha256: z.hash("sha256") }),
  size: z.number(),
});

const AppUpdatePipeline = z.object({
  pipeline_id: z.string(),
  operations: z.tuple([PipelineOperationDownload, PipelineOperationCrx3])
    .refine(([d, c]) => d.out.sha256 === c.in.sha256 && d.size === c.size),
});

const AppUpdate = z.object({
  appid: AppId,
  status: z.literal("ok"),
  updatecheck: z.object({
    status: z.literal("ok"),
    nextversion: z.string(),
    pipelines: z.tuple([AppUpdatePipeline]),
  }),
});

const Response = z.object({
  response: z.object({
    protocol: z.literal("4.0"),
    apps: z.array(z.any()),
  }),
});

interface FetchOmaha extends Request.Request<Addon, Error> {
  readonly _tag: "FetchOmaha";
  readonly id: AppId;
}

const FetchOmaha = Request.tagged<FetchOmaha>("FetchOmaha");

const FetchOmahaResolver = RequestResolver.make(
  (entries: ReadonlyArray<Request.Entry<FetchOmaha>>) =>
    fetch(OMAHA_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Goog-Update-Interactivity": "fg",
        "X-Goog-Update-Updater": `chromecrx-${CHROME_VERSION}`,
      },
      body: JSON.stringify({
        request: {
          protocol: "4.0",
          sessionid: `{${crypto.randomUUID()}}`,
          requestid: `{${crypto.randomUUID()}}`,
          "@updater": "chromecrx",
          updaterversion: CHROME_VERSION,
          prodversion: CHROME_VERSION,
          "@os": "linux",
          arch: "x64",
          dedup: "cr",
          acceptformat: "crx3,download,run",
          apps: entries.map(({ request }) => ({
            appid: request.id,
            version: "0",
            updatecheck: {},
          })),
        },
      }),
    }).pipe(
      Effect.tap(Console.log(`Making a request for ${entries.map((e) => e.request.id).join(", ")}`)),
      Effect.andThen(response.ok),
      Effect.andThen(response.text),
      Effect.map((r) => r.slice(4)),
      Effect.andThen(parseJSON),
      Effect.andThen(parseSchema(Response)),
      Effect.andThen((response) =>
        Effect.forEach(response.response.apps, (app) =>
          parseSchema(AppUpdate)(app).pipe(
            Effect.map((app) => ({
              version: app.updatecheck.nextversion,
              file: {
                url: app.updatecheck.pipelines[0].operations[0].urls[0].url,
                hash: toSRI("sha256")(decodeHex(app.updatecheck.pipelines[0].operations[0].out.sha256)),
              },
              passthru: { id: app.appid },
            })),
            Effect.exit,
            Effect.map((result) => ({ appid: app.appid, result })),
          ))
      ),
      Effect.map((results) =>
        entries.map((entry) => ({
          entry,
          result: results.find(({ appid }) => entry.request.id === appid)?.result,
        }))
      ),
      Effect.retry({ times: 2 }),
      Effect.andThen((results) =>
        Effect.forEach(results, ({ entry, result }) =>
          Request.complete(entry, result ?? Exit.fail(new Error("server did not return a response"))), {
          discard: true,
        })
      ),
      Effect.catch((error) =>
        Effect.forEach(entries, (entry) =>
          Request.completeEffect(entry, Effect.fail(error)), { discard: true })
      ),
    ),
);

export const fetchOmaha = (id: AppId) => Effect.request(FetchOmaha({ id }), FetchOmahaResolver).pipe(Effect.result);

// Third-party (Omaha v2)

const xmlName = (name: string) => z.object({ raw: z.literal(name) });

const Manifest = z.object({
  declaration: z.object({
    type: z.literal("declaration"),
    version: z.literal("1.0"),
    encoding: z.literal("UTF-8"),
  }),
  root: z.object({
    type: z.literal("element"),
    name: xmlName("gupdate"),
    attributes: z.object({
      xmlns: z.literal("http://www.google.com/update2/response"),
      protocol: z.literal("2.0"),
    }),
    children: listOf(z.object({
      type: z.literal("element"),
      name: xmlName("app"),
      attributes: z.object({ appid: AppId }),
      children: tupleOf([z.object({
        type: z.literal("element"),
        name: xmlName("updatecheck"),
        attributes: z.object({
          codebase: z.url(),
          version: z.string(),
        }),
      })]),
    })),
  }),
});

export const fetchChromium = (url: string) =>
  fetch(url).pipe(
    Effect.andThen(response.ok),
    Effect.andThen(response.text),
    Effect.andThen(parseXML),
    Effect.andThen(parseSchema(Manifest)),
    Effect.andThen((data) =>
      Effect.forEach(data.root.children, (app) =>
        fetch(app.children[0].attributes.codebase).pipe(
          Effect.tap(Console.log(`Downloading ${app.children[0].attributes.codebase} to hash it`)),
          Effect.andThen(response.ok),
          Effect.andThen(response.arrayBuffer),
          Effect.andThen(hash("SHA-256")),
          Effect.map(toSRI("sha256")),
          Effect.map((hash) => ({
            version: app.children[0].attributes.version,
            file: {
              url: app.children[0].attributes.codebase,
              hash,
            },
            passthru: { id: app.attributes.appid },
          } as Addon)),
          Effect.retry({ times: 2 }),
          Effect.result,
          Effect.map((result) => ([app.attributes.appid, result] as const)),
        ), { concurrency: 3 })
    ),
    Effect.map((items) => Object.fromEntries(items)),
    Effect.result,
  );
