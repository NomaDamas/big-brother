import { readFile } from "node:fs/promises";

const image = await readFile("tests/fixtures/images/known_match.bin");
const form = new FormData();
form.append("image", new Blob([image], { type: "image/jpeg" }), "known_match.jpg");

const response = await fetch("http://localhost:8080/v1/scan", {
  method: "POST",
  body: form,
});

if (!response.ok) {
  throw new Error(`scan failed: ${response.status}`);
}

console.log(await response.text());
