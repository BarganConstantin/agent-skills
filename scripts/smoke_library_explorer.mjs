#!/usr/bin/env node
// A dependency-free UI behavior smoke for the offline explorer. Simulates the
// minimal browser DOM contract used by the shipped local HTML, without network.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext, Script} from "node:vm";

const page = readFileSync(new URL("../docs/library-explorer.html", import.meta.url), "utf8");
const dataMatch = page.match(/<script id="library-data" type="application\/json">([\s\S]*?)<\/script>/);
const codeMatch = page.match(/<script>([\s\S]*?)<\/script>/);
assert(dataMatch && codeMatch, "Expected embedded JSON and local behavior script");
const data = JSON.parse(dataMatch[1]);

class Element {
  constructor(tagName) {
    this.tagName = tagName.toUpperCase();
    this.children = [];
    this.attributes = {};
    this.handlers = {};
    this.value = "";
    this.textContent = "";
    this.hidden = false;
  }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(key, fn) { this.handlers[key] = fn; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  querySelectorAll(selector) {
    assert.equal(selector, "button");
    return this.children.filter(child => child.tagName === "BUTTON");
  }
  remove() { this.removed = true; }
  focus() { document.activeElement = this; }
}
const ids = ["library-data", "filters", "search", "clear", "status", "cards",
             "empty", "total", "topic-count"];
const dom = Object.fromEntries(ids.map(id => [id, new Element(id === "search" ? "input" : "div")]));
dom["library-data"].textContent = dataMatch[1];
const document = {
  activeElement: new Element("body"),
  handlers: {},
  getElementById(id) {
    assert(dom[id], "Unexpected DOM ID: " + id);
    return dom[id];
  },
  createElement(type) { return new Element(type); },
  addEventListener(event, fn) { this.handlers[event] = fn; },
};
new Script(codeMatch[1], {filename: "library-explorer.html"}).runInNewContext(
  {document, console, JSON, String, Array, Number},
  {timeout: 3000}
);
assert.equal(dom.cards.children.length, data.entries.length,
  "All unique sources must initially be visible");
assert.equal(dom.total.textContent, String(data.entries.length).padStart(2, "0"));
assert.equal(dom.filters.children.length,
  data.categories.filter(category => category.id !== "inbox").length + 1,
  "Empty inbox should not be shown as a filter");
const backend = dom.filters.children.find(el => el.textContent.startsWith("Backend"));
assert(backend, "Backend filter must be available");
backend.handlers.click();
const expectedBackend = data.entries.filter(el => el.categories.includes("backend")).length;
assert.equal(dom.cards.children.length, expectedBackend, "Backend filter must narrow results");
assert.equal(backend.attributes["aria-pressed"], "true");
assert(dom.cards.children.every(el => el.children.some(child => child.tagName === "A")));
dom.search.value = "oasdiff";
dom.search.handlers.input();
assert.equal(dom.cards.children.length, 1, "Text search and category filtering must combine");
dom.search.value = "unrelated-impossible-query";
dom.search.handlers.input();
assert.equal(dom.cards.children.length, 0);
assert.equal(dom.empty.hidden, false, "No-match feedback should appear");
dom.clear.handlers.click();
assert.equal(dom.search.value, "");
assert.equal(dom.cards.children.length, expectedBackend, "Clear preserves category");
const all = dom.filters.children[0];
all.handlers.click();
assert.equal(dom.cards.children.length, data.entries.length);
const event = {key: "/", ctrlKey: false, metaKey: false, altKey: false,
               preventDefault() { this.prevented = true; }};
document.handlers.keydown(event);
assert.equal(event.prevented, true);
assert.equal(document.activeElement, dom.search, "Slash focuses the search input");
for (const card of dom.cards.children) {
  const link = card.children.find(child => child.tagName === "A");
  assert(link.href.startsWith("https://github.com/"), "Only official original GitHub links expected");
  assert.equal(link.rel, "noopener noreferrer");
}
console.log("Offline explorer UI smoke passed: " + data.entries.length +
            " sources, live filters, combined search, keyboard and links.");
