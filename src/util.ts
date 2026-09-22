import * as z from "@zod/zod";
import { Effect } from "effect";
import { parse } from "@std/xml";
import { encodeBase64, decodeHex } from "@std/encoding";

export const USER_AGENT = `NixBrowserAddons/1.0.0 (+https://github.com/andre4ik3/nix-browser-addons)`;

export interface Addon {
  version: string;
  file: {
    url: string;
    hash: string;
  };
  passthru: {
    id: string;
  };
};

export const fetch = (input: string | URL | Request, init?: RequestInit) =>
  Effect.tryPromise(() =>
    globalThis.fetch(input, {
      ...init,
      headers: {
        ...init?.headers,
        "User-Agent": USER_AGENT,
      },
    },
  ),
);

export const response = {
  ok: (r: Response) => r.ok ? Effect.succeed(r) : Effect.fail(new Error(`${r.status} ${r.statusText}`)),
  text: (r: Response) => Effect.tryPromise(() => r.text()),
  arrayBuffer: (r: Response) => Effect.tryPromise(() => r.arrayBuffer()),
} as const;

export const hash = (s: "SHA-256") => (b: ArrayBuffer) => Effect.tryPromise(() => crypto.subtle.digest(s, b));

export const toSRI = (s: string) => (b: ArrayBuffer | Uint8Array) => `${s}-${encodeBase64(b)}`;

export const parseJSON = (s: string) => Effect.try(() => JSON.parse(s));

export const parseXML = (s: string) => Effect.try(() => parse(s));

export function parseSchema<S extends z.ZodType>(schema: S) {
  return (data: unknown) => Effect.try(() => schema.parse(data));
}

export function listOf<S extends z.ZodType>(
  schema: S,
) {
  return z.array(z.unknown()).transform((items): z.output<S>[] => {
    return items.flatMap((item) => {
      const result = schema.safeParse(item);
      return result.success ? [result.data] : [];
    });
  });
}

type Outputs<S extends readonly z.ZodType[]> = {
  -readonly [K in keyof S]: z.output<S[K]>;
};

export function tupleOf<const S extends readonly z.ZodType[]>(schemas: S) {
  return z.array(z.unknown()).transform((items, ctx): Outputs<S> => {
    const out: unknown[] = [];
    let schemaIndex = 0;

    for (const item of items) {
      const schema = schemas[schemaIndex];
      if (!schema) break;

      const result = schema.safeParse(item);

      if (result.success) {
        out.push(result.data);
        schemaIndex++;
      }
    }

    if (schemaIndex !== schemas.length) {
      ctx.addIssue({
        code: "custom",
        message: `Could not find all tuple elements`,
      });

      return z.NEVER;
    }

    return out as Outputs<S>;
  });
}

export const digestToSRI = (hash: string) => {
  const [alg, hex] = hash.split(":", 2);
  return toSRI(alg)(decodeHex(hex));
}
