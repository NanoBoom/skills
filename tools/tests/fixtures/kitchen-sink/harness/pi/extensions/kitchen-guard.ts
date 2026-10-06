/**
 * Fixture Pi hook: the Pi counterpart of the Claude Code PreToolUse hook.
 * Writes a marker when KITCHEN_PI_MARKER is set, so a test can see it loaded.
 */

import { writeFileSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
	if (process.env.KITCHEN_PI_MARKER) writeFileSync(`${process.env.KITCHEN_PI_MARKER}.guard`, "loaded");

	pi.on("tool_call", async (event) => {
		if (event.toolName !== "bash") return undefined;
		return undefined;
	});
}
