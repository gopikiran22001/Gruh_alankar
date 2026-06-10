"""
Gruha Alankara — Web Agent

Scrapes furniture and decor products from Indian e-commerce sites
using Playwright (for JS-rendered) and BeautifulSoup (for static pages).
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.agents.base_agent import BaseAgent
from app.agents.schemas import AgentResult, AgentTask, TaskStatusEnum
from app.database.mongo import insert_one, find_many
from config.constants import AgentName, MongoCollection, ScrapingSource
from config.logging_config import get_logger

logger = get_logger(__name__)


class WebAgent(BaseAgent):
    """
    Web scraping agent for product discovery and price comparison.

    Sources: Pepperfry, Urban Ladder, IKEA India, Amazon India.
    Uses httpx + BeautifulSoup for scraping with rate limiting.
    """

    name = AgentName.WEB
    description = "Discovers products, scrapes prices, and finds trends from Indian e-commerce sites"
    supported_task_types = [
        "scrape_products",
        "compare_prices",
        "discover_trends",
        "search_products",
    ]
    requires_internet = True
    estimated_latency_s = 30.0

    def __init__(self) -> None:
        super().__init__()
        self._http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )

    def _get_capabilities(self) -> List[str]:
        return [
            "Search and scrape furniture products from Pepperfry, Urban Ladder, IKEA, Amazon",
            "Compare prices across multiple e-commerce platforms",
            "Discover trending styles and products",
            "Extract product details: name, price, images, ratings, specifications",
        ]

    async def execute(self, task: AgentTask) -> AgentResult:
        handlers = {
            "scrape_products": self._scrape_products,
            "compare_prices": self._compare_prices,
            "discover_trends": self._discover_trends,
            "search_products": self._scrape_products,  # alias
        }

        handler = handlers.get(task.task_type)
        if not handler:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=[f"Unknown task type: {task.task_type}"],
            )

        return await handler(task)

    async def _scrape_products(self, task: AgentTask) -> AgentResult:
        """Search and scrape products from specified sources."""
        query = task.parameters.get("query", "")
        sources = task.parameters.get("sources", ScrapingSource.ALL)
        max_results = task.parameters.get("max_results", 10)
        category = task.parameters.get("category", "furniture")

        if not query:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Search query is required"],
            )

        all_products: List[Dict[str, Any]] = []
        errors: List[str] = []

        for source in sources:
            try:
                products = await self._scrape_source(source, query, max_results)
                all_products.extend(products)
                logger.info("source_scraped", source=source, count=len(products))
            except Exception as e:
                error_msg = f"Failed to scrape {source}: {str(e)}"
                errors.append(error_msg)
                logger.warning("scrape_failed", source=source, error=str(e))

        # Store scraped products in MongoDB
        for product in all_products:
            product["category"] = category
            product["search_query"] = query
            product["scraped_at"] = datetime.now(timezone.utc)
            try:
                insert_one(MongoCollection.SCRAPED_PRODUCTS, product)
            except Exception:
                pass  # Don't fail the entire operation for a DB write failure

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS if all_products else TaskStatusEnum.FAILED,
            data={
                "products": all_products,
                "total_found": len(all_products),
                "sources_searched": sources,
                "query": query,
            },
            errors=errors,
            confidence_score=1.0 if not errors else 0.7,
        )

    async def _compare_prices(self, task: AgentTask) -> AgentResult:
        """Compare prices for a product across sources."""
        product_name = task.parameters.get("product_name", "")

        if not product_name:
            return AgentResult(
                task_id=task.task_id,
                agent_name=self.name,
                status=TaskStatusEnum.FAILED,
                errors=["Product name is required"],
            )

        # Search across all sources
        all_results: List[Dict[str, Any]] = []
        for source in ScrapingSource.ALL:
            try:
                products = await self._scrape_source(source, product_name, max_results=5)
                for p in products:
                    p["source"] = source
                all_results.extend(products)
            except Exception as e:
                logger.warning("compare_scrape_failed", source=source, error=str(e))

        # Sort by price
        priced_results = [r for r in all_results if r.get("price")]
        priced_results.sort(key=lambda x: x.get("price", float("inf")))

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "product_name": product_name,
                "comparisons": priced_results,
                "cheapest": priced_results[0] if priced_results else None,
                "most_expensive": priced_results[-1] if priced_results else None,
                "total_found": len(priced_results),
            },
        )

    async def _discover_trends(self, task: AgentTask) -> AgentResult:
        """Discover trending styles and products."""
        category = task.parameters.get("category", "furniture")

        trending_queries = [
            f"trending {category} 2025",
            f"bestselling {category} India",
            f"popular interior design {category}",
        ]

        all_trends: List[Dict[str, Any]] = []
        for query in trending_queries:
            try:
                products = await self._scrape_source(
                    ScrapingSource.PEPPERFRY, query, max_results=5
                )
                all_trends.extend(products)
            except Exception as e:
                logger.warning("trend_scrape_failed", query=query, error=str(e))

        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            status=TaskStatusEnum.SUCCESS,
            data={
                "trends": all_trends,
                "category": category,
                "total_found": len(all_trends),
            },
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Source-specific Scrapers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    async def _scrape_source(
        self, source: str, query: str, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Route to source-specific scraper."""
        scrapers = {
            ScrapingSource.PEPPERFRY: self._scrape_pepperfry,
            ScrapingSource.URBAN_LADDER: self._scrape_urban_ladder,
            ScrapingSource.IKEA: self._scrape_ikea,
            ScrapingSource.AMAZON: self._scrape_amazon,
        }

        scraper = scrapers.get(source)
        if not scraper:
            return []

        return await scraper(query, max_results)

    async def _scrape_pepperfry(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Scrape products from Pepperfry."""
        url = f"https://www.pepperfry.com/search?q={quote_plus(query)}"
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            products = []
            product_cards = soup.select(".product-card, .clipCardContainer, [data-productid]")

            for card in product_cards[:max_results]:
                product = self._extract_product_data(card, ScrapingSource.PEPPERFRY, url)
                if product.get("name"):
                    products.append(product)

            return products
        except Exception as e:
            logger.warning("pepperfry_scrape_error", error=str(e))
            return []

    async def _scrape_urban_ladder(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Scrape products from Urban Ladder."""
        url = f"https://www.urbanladder.com/search?q={quote_plus(query)}"
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            products = []
            product_cards = soup.select(".product-card, .product-listing-card, .product-item")

            for card in product_cards[:max_results]:
                product = self._extract_product_data(card, ScrapingSource.URBAN_LADDER, url)
                if product.get("name"):
                    products.append(product)

            return products
        except Exception as e:
            logger.warning("urban_ladder_scrape_error", error=str(e))
            return []

    async def _scrape_ikea(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Scrape products from IKEA India."""
        url = f"https://www.ikea.com/in/en/search/?q={quote_plus(query)}"
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            products = []
            product_cards = soup.select(".serp-grid__item, .product-compact, .plp-fragment-wrapper")

            for card in product_cards[:max_results]:
                product = self._extract_product_data(card, ScrapingSource.IKEA, url)
                if product.get("name"):
                    products.append(product)

            return products
        except Exception as e:
            logger.warning("ikea_scrape_error", error=str(e))
            return []

    async def _scrape_amazon(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Scrape products from Amazon India."""
        url = f"https://www.amazon.in/s?k={quote_plus(query)}"
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            products = []
            product_cards = soup.select("[data-component-type='s-search-result']")

            for card in product_cards[:max_results]:
                product = self._extract_amazon_product(card)
                if product.get("name"):
                    products.append(product)

            return products
        except Exception as e:
            logger.warning("amazon_scrape_error", error=str(e))
            return []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Data Extraction Helpers
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _extract_product_data(
        self, card: Any, source: str, search_url: str
    ) -> Dict[str, Any]:
        """Generic product data extraction from HTML card."""
        name = ""
        price = None
        image_url = ""
        product_url = ""
        rating = None

        # Try multiple selectors for name
        name_el = card.select_one(
            "h3, h4, .product-name, .product-title, "
            "[class*='name'], [class*='title'], a[title]"
        )
        if name_el:
            name = name_el.get_text(strip=True) or name_el.get("title", "")

        # Try to extract price
        price_el = card.select_one(
            ".price, .product-price, [class*='price'], "
            "[class*='Price'], span[class*='amount']"
        )
        if price_el:
            price_text = price_el.get_text(strip=True)
            price = self._parse_price(price_text)

        # Image
        img_el = card.select_one("img")
        if img_el:
            image_url = img_el.get("src", "") or img_el.get("data-src", "")

        # Product link
        link_el = card.select_one("a[href]")
        if link_el:
            href = link_el.get("href", "")
            if href and not href.startswith("http"):
                base = ScrapingSource.BASE_URLS.get(source, "")
                product_url = f"{base}{href}"
            else:
                product_url = href

        # Rating
        rating_el = card.select_one("[class*='rating'], [class*='star']")
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            try:
                rating = float(rating_text.split("/")[0].strip())
            except (ValueError, IndexError):
                pass

        return {
            "name": name,
            "price": price,
            "image_url": image_url,
            "product_url": product_url,
            "rating": rating,
            "source": source,
            "product_id": hashlib.md5(f"{source}:{name}".encode()).hexdigest()[:12],
        }

    def _extract_amazon_product(self, card: Any) -> Dict[str, Any]:
        """Amazon-specific product extraction."""
        name = ""
        price = None
        image_url = ""
        product_url = ""
        rating = None

        name_el = card.select_one("h2 a span, .a-text-normal")
        if name_el:
            name = name_el.get_text(strip=True)

        price_el = card.select_one(".a-price .a-offscreen, .a-price-whole")
        if price_el:
            price = self._parse_price(price_el.get_text(strip=True))

        img_el = card.select_one("img.s-image")
        if img_el:
            image_url = img_el.get("src", "")

        link_el = card.select_one("h2 a")
        if link_el:
            href = link_el.get("href", "")
            product_url = f"https://www.amazon.in{href}" if href.startswith("/") else href

        rating_el = card.select_one(".a-icon-alt")
        if rating_el:
            try:
                rating = float(rating_el.get_text(strip=True).split(" ")[0])
            except (ValueError, IndexError):
                pass

        return {
            "name": name,
            "price": price,
            "image_url": image_url,
            "product_url": product_url,
            "rating": rating,
            "source": ScrapingSource.AMAZON,
            "product_id": hashlib.md5(f"amazon:{name}".encode()).hexdigest()[:12],
        }

    @staticmethod
    def _parse_price(price_text: str) -> Optional[float]:
        """Parse price from text like '₹12,999' or 'Rs. 12999.00'."""
        import re
        if not price_text:
            return None
        # Remove currency symbols and commas
        cleaned = re.sub(r"[₹Rs.,\s]", "", price_text)
        try:
            return float(cleaned)
        except ValueError:
            return None
