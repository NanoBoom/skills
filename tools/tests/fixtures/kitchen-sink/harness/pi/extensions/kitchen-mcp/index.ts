/**
 * Fixture Pi extension in a directory, standing in for an MCP client. Pi core has
 * no MCP, so a plugin brings its servers to Pi as an extension like this one.
 */

import { writeFileSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { serverName } from "./server";

export default function (pi: ExtensionAPI) {
	if (process.env.KITCHEN_PI_MARKER) writeFileSync(`${process.env.KITCHEN_PI_MARKER}.mcp`, serverName());

	pi.on("session_start", async () => undefined);
}
