import * as z from "@zod/zod";
import { Effect } from "effect";
import { Addon, digestToSRI, fetch, parseJSON, parseSchema, response } from "./util.ts";

const BASE_URL = "https://api.github.com";
const API_VERSION = "2026-03-10";

const ReleaseAsset = z.object({
  browser_download_url: z.url(),
  digest: z.templateLiteral(["sha256:", z.hash("sha256")]),
  state: z.literal("uploaded"),
});

const Release = z.object({
  tag_name: z.string().transform((v) => v.startsWith("v") ? v.slice(1) : v),
  assets: z.array(ReleaseAsset).nonempty(),
});

export interface FetchGitHubParams {
  owner: string;
  repo: string;
  id: string;
}

export const fetchGitHub = ({ owner, repo, id }: FetchGitHubParams) =>
  fetch(
    `${BASE_URL}/repos/${owner}/${repo}/releases/latest`,
    { headers: { "X-GitHub-Api-Version": API_VERSION } },
  ).pipe(
    Effect.andThen(response.ok),
    Effect.andThen(response.text),
    Effect.andThen(parseJSON),
    Effect.andThen(parseSchema(Release)),
    Effect.map((release) => ({
      version: release.tag_name,
      file: {
        url: release.assets[0].browser_download_url,
        hash: digestToSRI(release.assets[0].digest),
      },
      passthru: { id },
    } as Addon)),
    Effect.result,
  );
