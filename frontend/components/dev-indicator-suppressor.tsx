"use client";

import { useEffect } from "react";

function isDevIndicatorElement(node: Element): boolean {
  if (!(node instanceof HTMLElement)) {
    return false;
  }
  if (node.dataset.nextjsDevIndicator) {
    return true;
  }
  const ariaLabel = node.getAttribute("aria-label")?.toLowerCase() ?? "";
  if (ariaLabel.includes("next.js dev indicator")) {
    return true;
  }
  const link = node.querySelector<HTMLAnchorElement>("a[href*='nextjs.org']");
  if (link) {
    const linkLabel = `${link.getAttribute("aria-label") ?? ""} ${link.textContent ?? ""}`.toLowerCase();
    if (linkLabel.includes("next.js")) {
      return true;
    }
  }
  return false;
}

export default function DevIndicatorSuppressor() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") {
      return;
    }

    const removeIndicator = () => {
      const candidates = new Set<Element>();
      document.querySelectorAll("[data-nextjs-dev-indicator]").forEach((node) => candidates.add(node));
      document.querySelectorAll("[data-nextjs-portal]").forEach((node) => candidates.add(node));

      candidates.forEach((node) => {
        if (isDevIndicatorElement(node)) {
          node.remove();
          return;
        }
        const childIndicator = Array.from(node.children).find((child) => isDevIndicatorElement(child));
        childIndicator?.remove();
      });
    };

    removeIndicator();
    const observer = new MutationObserver(removeIndicator);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return null;
}
