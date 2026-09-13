"""
Multi-Engine Web & Encyclopedic Research Engine
Exclusively queries live Wikipedia REST API and DuckDuckGo Search.
Zero hardcoded data fallbacks: network/retrieval failures return UNVERIFIED.
"""

import urllib.request
import urllib.parse
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
from core.schemas import EvidenceItem


class WebSearchEngine:
    def __init__(self, enable_live: bool = True):
        self.enable_live = enable_live
        self.cache: Dict[str, List[EvidenceItem]] = {}
        self.last_stats: Dict[str, int] = {"wikipedia": 0, "duckduckgo": 0, "total": 0}
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    def search_claim(self, claim: str, question: str = "") -> List[EvidenceItem]:
        cache_key = claim.strip().lower()
        if cache_key in self.cache:
            return self.cache[cache_key]

        evidence_list: List[EvidenceItem] = []
        wiki_count = 0
        ddg_count = 0

        if self.enable_live:
            query = self._formulate_query(claim, question)

            # 1. Primary Encyclopedic Engine: Wikipedia REST API
            wiki_results = self._fetch_wikipedia_evidence(query)
            if wiki_results:
                evidence_list.extend(wiki_results)
                wiki_count = len(wiki_results)

            # 2. Live Web Engine: DuckDuckGo Search
            ddg_results = self._fetch_live_web_evidence(query)
            if ddg_results:
                evidence_list.extend(ddg_results)
                ddg_count = len(ddg_results)

        # Deduplicate and rank by domain credibility tier
        seen_urls = set()
        deduped: List[EvidenceItem] = []
        for ev in evidence_list:
            if ev.source_url not in seen_urls:
                seen_urls.add(ev.source_url)
                deduped.append(ev)

        deduped.sort(key=lambda x: x.reliability_weight, reverse=True)
        self.cache[cache_key] = deduped
        self.last_stats = {
            "wikipedia": wiki_count,
            "duckduckgo": ddg_count,
            "total": len(deduped)
        }
        return deduped

    def _formulate_query(self, claim: str, question: str) -> str:
        clean = re.sub(r"[^\w\s₹$€£\.-]", "", claim)
        words = [w for w in clean.split() if len(w) > 2 and w.lower() not in {
            "this", "that", "with", "from", "best", "choice", "top", "costs", "features", "provides"
        }]
        if len(words) > 7:
            return " ".join(words[:7])
        return " ".join(words) if words else claim[:40]

    def _fetch_wikipedia_evidence(self, query: str) -> List[EvidenceItem]:
        """Queries Wikipedia Search API & REST Summary API for verified factual extracts."""
        results: List[EvidenceItem] = []
        try:
            # 1. Full-text search on Wikipedia
            search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
            req = urllib.request.Request(search_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    search_items = data.get("query", {}).get("search", [])
                    for item in search_items[:3]:
                        title = item.get("title", "")
                        raw_snippet = item.get("snippet", "")
                        clean_snippet = BeautifulSoup(raw_snippet, "html.parser").get_text()
                        page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        
                        # Optionally fetch high-density summary for top match
                        if title and len(results) == 0:
                            try:
                                sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                                sum_req = urllib.request.Request(sum_url, headers={"User-Agent": self.user_agent})
                                with urllib.request.urlopen(sum_req, timeout=3) as sum_resp:
                                    if sum_resp.status == 200:
                                        sum_data = json.loads(sum_resp.read().decode("utf-8"))
                                        extract = sum_data.get("extract", "")
                                        if extract:
                                            clean_snippet = f"{extract[:350]} ... {clean_snippet}"
                            except Exception:
                                pass

                        if clean_snippet:
                            results.append(EvidenceItem(
                                source_url=page_url,
                                source_title=f"Wikipedia: {title}",
                                snippet=clean_snippet[:500],
                                reliability_weight=0.90
                            ))
        except Exception:
            pass
        return results


    def _fetch_live_web_evidence(self, query: str) -> List[EvidenceItem]:
        """Queries DuckDuckGo Lite for live web snippets and product citations."""
        results: List[EvidenceItem] = []
        try:
            data = urllib.parse.urlencode({"q": query}).encode("utf-8")
            req = urllib.request.Request(
                "https://lite.duckduckgo.com/lite/",
                data=data,
                headers={"User-Agent": self.user_agent}
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    soup = BeautifulSoup(response.read(), "html.parser")
                    links = soup.find_all("a", class_="result-link")
                    snippets = soup.find_all("td", class_="result-snippet")
                    for i in range(min(len(links), len(snippets), 4)):
                        raw_url = links[i].get("href", "")
                        title = links[i].text.strip()
                        snippet = snippets[i].text.strip()
                        url = self._clean_ddg_url(raw_url)
                        if url and snippet:
                            weight = self._evaluate_domain_credibility(url)
                            results.append(EvidenceItem(
                                source_url=url,
                                source_title=title or "Web Citation",
                                snippet=snippet,
                                reliability_weight=weight
                            ))
        except Exception:
            pass
        return results

    def _clean_ddg_url(self, raw_url: str) -> str:
        if "duckduckgo.com/l/?uddg=" in raw_url:
            match = re.search(r"uddg=([^&]+)", raw_url)
            if match:
                return urllib.parse.unquote(match.group(1))
        return raw_url

    def _evaluate_domain_credibility(self, url: str) -> float:
        domain = urllib.parse.urlparse(url).netloc.lower()
        tier1 = [r"\.gov\b", r"\.edu\b", r"sony\.", r"realme\.", r"boat-lifestyle\.", r"apple\.", r"microsoft\.", r"github\.", r"cdc\.gov", r"nih\.gov", r"sec\.gov"]
        if any(re.search(p, domain) for p in tier1):
            return 1.0
        tier2 = [r"amazon\.", r"flipkart\.", r"gsmarena\.", r"rtings\.", r"theverge\.", r"cnet\.", r"techradar\.", r"wikipedia\.org", r"reuters\.", r"bloomberg\.", r"nature\.com"]
        if any(re.search(p, domain) for p in tier2):
            return 0.85
        return 0.50
