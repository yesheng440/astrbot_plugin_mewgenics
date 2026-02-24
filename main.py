import os
import uuid
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
        
        # 使用 UUID 生成唯一文件名，杜绝路径遍历和并发冲突覆盖问题
        safe_filename = f"{uuid.uuid4().hex}.png"
        save_path = os.path.join(self.temp_dir, safe_filename)

        try:
            async with async_playwright() as p:
                # 使用 async with 管理 browser，确保任何异常下都能正确释放浏览器进程资源
                async with await p.chromium.launch(headless=True) as browser:
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

                    if category != "能力":
                        # 定位到 navbar 区域并点击
                        await page.locator(".navbar").get_by_text(category, exact=True).click()

                    # 输入搜索内容
                    await page.locator("#searchInput").fill(item_name)

                    # 使用 Playwright 的内置 filter() 避免直接拼接入 CSS 选择器，防止选择器注入
                    row_locator = page.locator("#tableBody tr").filter(has_text=item_name).first

                    try:
                        # 弃用 wait_for_timeout，改用状态驱动的显式等待
                        await row_locator.wait_for(state="visible", timeout=3000)
                        is_found = True
                    except Exception:
                        is_found = False

                    if is_found:
                        await row_locator.screenshot(path=save_path)
                        yield event.image_result(save_path)
                    else:
                        yield event.plain_result(
                            f"图鉴的【{category}】里似乎没有找到包含【{item_name}】的记录喵~"
                        )

        except Exception as e:
            logger.error(f"Mewgenics截图插件运行失败: {e}")
            yield event.plain_result(
                "查询出错啦，可能是网络超时或服务器开小差了喵~ 请稍后再试！"
            )
            
        finally:
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception as e:
                    logger.error(f"清理临时文件失败: {e}")

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
