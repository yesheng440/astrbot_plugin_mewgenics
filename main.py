import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from playwright.async_api import async_playwright


@register("astrbot_plugin_mewgenics", "YourName", "Mewgenics全图鉴查询插件", "1.0.0")
class MewgenicsFinder(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.temp_dir = "temp_screenshots"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    # 搜索和截图方法
    async def _query_wiki_core(
        self, event: AstrMessageEvent, category: str, item_name: str
    ):
        yield event.plain_result(
            f"正在前往 Mewgenics 图鉴的【{category}】区检索【{item_name}】，请稍候..."
        )

        target_url = "https://mewcodex.pages.dev/?lang=zh"
        save_path = f"{self.temp_dir}/{item_name}.png"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                await page.set_viewport_size({"width": 1400, "height": 900})
                await page.goto(target_url, wait_until="networkidle")

                # 隐藏悬浮公告和语言切换
                await page.add_style_tag(
                    content="""
                    #announcementModal, 
                    .announcement-modal,
                    .language-toggle { 
                        display: none !important; 
                    }
                """
                )

                # 如果是查非“能力”的其他选项，先让浏览器点击顶部导航栏
                if category != "能力":
                    # 定位到 navbar 区域，并精准点击对应的文字标签
                    await (
                        page.locator(".navbar")
                        .get_by_text(category, exact=True)
                        .click()
                    )
                    # 稍微等半秒钟，让网页完成列表的切换渲染
                    await page.wait_for_timeout(500)

                # 后续逻辑保持不变：输入搜索 -> 找结果 -> 截图
                await page.locator("#searchInput").fill(item_name)
                await page.wait_for_timeout(800)

                row_locator = page.locator(
                    f"#tableBody tr:has-text('{item_name}')"
                ).first

                if await row_locator.count() > 0:
                    await row_locator.screenshot(path=save_path)
                    yield event.image_result(save_path)
                else:
                    yield event.plain_result(
                        f"图鉴的【{category}】里似乎没有找到包含【{item_name}】的记录喵~"
                    )

                await browser.close()

        except Exception as e:
            logger.error(f"截图插件运行失败: {e}")
            yield event.plain_result(
                f"查询出错啦，可能是网络超时或容器环境问题。\n错误信息: {str(e)}"
            )

    # ================= 下面是各个具体的指令入口 =================

    @filter.command("查能力")
    async def query_ability(self, event: AstrMessageEvent, name: str):
        """查能力 [能力名称]"""
        async for res in self._query_wiki_core(event, "能力", name):
            yield res

    @filter.command("查被动")
    async def query_passive(self, event: AstrMessageEvent, name: str):
        """查被动 [被动名称]"""
        async for res in self._query_wiki_core(event, "被动", name):
            yield res

    @filter.command("查物品")
    async def query_item(self, event: AstrMessageEvent, name: str):
        """查物品 [物品名称]"""
        async for res in self._query_wiki_core(event, "物品", name):
            yield res

    @filter.command("查突变")
    async def query_mutation(self, event: AstrMessageEvent, name: str):
        """查突变 [突变名称]"""
        async for res in self._query_wiki_core(event, "突变", name):
            yield res

    @filter.command("查角色")
    async def query_character(self, event: AstrMessageEvent, name: str):
        """查角色 [角色名称]"""
        async for res in self._query_wiki_core(event, "角色", name):
            yield res
