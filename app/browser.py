from contextlib import asynccontextmanager
from playwright.async_api import async_playwright

@asynccontextmanager
async def browser_context():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        try:
            yield context
        finally:
            await context.close()
            await browser.close()

async def get_page_text(url: str) -> str:
    async with browser_context() as ctx:
        page = await ctx.new_page()
        await page.goto(url, wait_until="networkidle")
        return await page.inner_text("body")

async def get_page_html(url: str) -> str:
    async with browser_context() as ctx:
        page = await ctx.new_page()
        await page.goto(url, wait_until="networkidle")
        return await page.content()
