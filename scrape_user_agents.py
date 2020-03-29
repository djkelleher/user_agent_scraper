from pyppeteer_spider.spider import PyppeteerSpider
from pathlib import Path
import logging
import asyncio
import random
import json
import re

browser_regexs = {
    'edge': re.compile(r'Edge\/(\d{1,2})\.\d{3,5}'),
    'chrome': re.compile(r'Chrome\/(\d{1,2})\.\d{1}\.\d{3,4}\.\d{1,4}'),
    'firefox': re.compile(r'Firefox\/(\d{1,2})\.\d{1,2}'),
    'yabrowser': re.compile(r'YaBrowser\/(\d{2})\.\d{1,2}\.\d{1,4}\.\d{1,4}')
}


def filter_user_agents(user_agents, browser_name, min_major_version):
    """
    Get list of user agents with major version >= min_major_version.

    Args:
        user_agents (list): user agent strings.
        browser_name (str): chrome|firefox|edge|yandex-browser.
        min_major_version (int): oldest allowable browser major version.

    Returns:
        set: user agent strings.
    """
    filtered_user_agents = set()
    browser_name = browser_name.lower()
    if browser_name in browser_regexs:
        print(
            f"Filtering {len(user_agents)} {browser_name} user agents with min_major_version {min_major_version}."
        )
        version_re = browser_regexs[browser_name]
        for ua in user_agents:
            match = version_re.search(ua)
            if match is not None:
                major_version = int(match.group(1))
                if major_version >= int(min_major_version):
                    filtered_user_agents.add(ua)
    else:
        print(
            f"No version regex found for browser {browser_name}. Browser should match one of: {', '.join(browser_regexs.keys())}"
        )
    print(
        f"{len(filtered_user_agents)} {browser_name} user agents remain after filtering."
    )
    return filtered_user_agents


async def scrape_useragentstring(spider, browser_name, min_major_version):
    """Scrape user agents from useragentstring.com

    Args:
        spider (PyppeteerSpider): spider instance.
        browser_name (str): chrome|firefox|edge.
        min_major_version (int): oldest allowable browser major version.

    Returns:
        set: user agent strings.
    """
    url = f'http://useragentstring.com/pages/useragentstring.php?name={browser_name}'
    page = await spider.get(url)
    user_agents = set([
        await page.evaluate('(element) => element.innerText', ele)
        for ele in await page.xpath('//*[@id="liste"]/ul//a')
    ])
    await spider.set_idle(page)
    print(f"Extracted {len(user_agents)} user agents from {url}")
    return filter_user_agents(user_agents, browser_name, min_major_version)


async def scrape_whatismybrowser(spider, browser_name, min_major_version):
    """Scrape user agents from whatismybrowser.com

    Args:
        spider (PyppeteerSpider): spider instance.
        browser_name (str): chrome|firefox|edge|yandex-browser.
        min_major_version (int): oldest allowable browser major version.

    Returns:
        set: user agent strings.
    """
    page = await spider.get(
        f'http://developers.whatismybrowser.com/useragents/explore/software_name/{browser_name}/1'
    )
    # find last page number.
    last_page_ele = await page.xpath(
        '//*[@id="pagination"]/a[contains(text(),"Last Page")]')
    last_page_text = await page.evaluate('(element) => element.innerText',
                                         last_page_ele[0])
    await spider.set_idle(page)
    last_page_num = re.search(r'\((\d{1,3})\)', last_page_text).group(1)
    user_agents = set()
    for i in range(1, int(last_page_num)):
        page = await spider.get(
            f'http://developers.whatismybrowser.com/useragents/explore/software_name/{browser_name}/{i+1}'
        )
        await asyncio.sleep(random.uniform(3, 5))
        user_agents.update([
            await page.evaluate('(element) => element.innerText', ele)
            for ele in await page.xpath('//*[@class="useragent"]/a')
        ])
        await spider.set_idle(page)
    return filter_user_agents(user_agents, browser_name, min_major_version)


def save_user_agents(user_agents, save_path):
    """Save list of user agents to a file."""
    with save_path.open(mode='a+') as outfile:
        for ua in user_agents:
            outfile.write(ua + "\n")
