import { defineLive } from "next-sanity/live";
import { client } from "./client";

export const { SanityLive, useLive } = defineLive({
  client,
});
