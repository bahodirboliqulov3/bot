import asyncio
import logging
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.types import FSInputFile
from sqlalchemy import select
from app.database.models.test import Test, TestStatus
from app.database.repositories.channel_repo import ChannelRepository
from app.database.repositories.result_repo import ResultRepository
from app.database.repositories.test_repo import TestRepository
from app.database.session import async_session_factory
from app.services.certificate_service import CertificateService

logger = logging.getLogger("scheduler")


class SchedulerService:
    @staticmethod
    async def start_scheduler_loop(bot: Bot, interval_seconds: int = 30):
        """
        Background loop that checks for:
        1. Scheduled tests whose start_time has arrived -> Mark ACTIVE
        2. Active tests whose end_time has arrived -> Mark FINISHED and auto-publish results to channels
        """
        logger.info("Background Scheduler Service started (checking every %ds)...", interval_seconds)
        while True:
            try:
                await SchedulerService.check_and_process_tests(bot)
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e, exc_info=True)
            await asyncio.sleep(interval_seconds)

    @staticmethod
    async def check_and_process_tests(bot: Bot):
        now = datetime.now(timezone.utc)

        async with async_session_factory() as session:
            test_repo = TestRepository(session)
            result_repo = ResultRepository(session)
            channel_repo = ChannelRepository(session)

            # 1. Auto-Start Scheduled Tests
            stmt_sched = select(Test).where(
                Test.status == TestStatus.SCHEDULED,
                Test.start_time <= now
            )
            res_sched = await session.execute(stmt_sched)
            scheduled_tests = res_sched.scalars().all()

            for test in scheduled_tests:
                test.status = TestStatus.ACTIVE
                await session.flush()
                logger.info("Test %s (%s) has been automatically ACTIVATED.", test.title, test.code)
                try:
                    if test.author and test.author.telegram_id:
                        await bot.send_message(
                            chat_id=test.author.telegram_id,
                            text=f"🟢 <b>Rejalashtirilgan test boshlandi!</b>\n\n"
                                 f"📝 Test: <b>{test.title}</b>\n"
                                 f"🔑 Kodi: <code>{test.code}</code>\n"
                                 f"O‘quvchilar testni yechishni boshlashlari mumkin.",
                            parse_mode="HTML"
                        )
                except Exception as e:
                    logger.warning("Could not notify author of test %s: %s", test.code, e)

            # 2. Auto-Finish Expired Tests & Publish Results
            stmt_expired = select(Test).where(
                Test.status == TestStatus.ACTIVE,
                Test.end_time.is_not(None),
                Test.end_time <= now
            )
            res_expired = await session.execute(stmt_expired)
            expired_tests = res_expired.scalars().all()

            for test in expired_tests:
                test.status = TestStatus.FINISHED
                await session.flush()
                logger.info("Test %s (%s) has EXPIRED and is now FINISHED.", test.title, test.code)

                # Fetch all results for this test
                results = await result_repo.get_test_results(test.id)
                total_participants = len(results)
                avg_score = sum(r.percentage for r in results) / total_participants if total_participants > 0 else 0

                # Leaderboard summary text
                summary_text = (
                    f"🏆 <b>«{test.title}» TESTI YAKUNLANDI!</b>\n\n"
                    f"🔑 Test kodi: <code>{test.code}</code>\n"
                    f"👥 Jami qatnashchilar: <b>{total_participants} ta</b>\n"
                    f"🎯 O‘rtacha ko‘rsatkich: <b>{avg_score:.1f}%</b>\n\n"
                )

                if results:
                    summary_text += "<b>🏅 TOP-10 G‘oliblar:</b>\n"
                    for idx, r in enumerate(results[:10], start=1):
                        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
                        uname = r.user.full_name if r.user else "O'quvchi"
                        summary_text += f"{medal} {uname} — {r.correct_count} ta ({r.percentage}% | {r.total_score} ball)\n"
                else:
                    summary_text += "Ushbu testda hech kim qatnashmadi."

                # Generate Result Sheet PDF
                pdf_path = None
                if results:
                    try:
                        pdf_path = CertificateService.generate_result_pdf(results, test.title, test.code)
                    except Exception as err:
                        logger.error("Error generating result PDF for test %s: %s", test.code, err)

                # Send to active channels
                channels = await channel_repo.get_active_channels()
                for ch in channels:
                    try:
                        if pdf_path and pdf_path.exists():
                            await bot.send_document(
                                chat_id=ch.channel_id,
                                document=FSInputFile(path=str(pdf_path), filename=f"Natijalar_{test.code}.pdf"),
                                caption=summary_text,
                                parse_mode="HTML"
                            )
                        else:
                            await bot.send_message(
                                chat_id=ch.channel_id,
                                text=summary_text,
                                parse_mode="HTML"
                            )
                    except Exception as ch_err:
                        logger.warning("Could not auto-post results to channel %s: %s", ch.channel_id, ch_err)

                # Send confirmation to test author
                try:
                    if test.author and test.author.telegram_id:
                        if pdf_path and pdf_path.exists():
                            await bot.send_document(
                                chat_id=test.author.telegram_id,
                                document=FSInputFile(path=str(pdf_path), filename=f"Natijalar_{test.code}.pdf"),
                                caption=f"⏰ <b>Test muddati tugadi va natijalar e'lon qilindi!</b>\n\n{summary_text}",
                                parse_mode="HTML"
                            )
                        else:
                            await bot.send_message(
                                chat_id=test.author.telegram_id,
                                text=f"⏰ <b>Test muddati tugadi!</b>\n\n{summary_text}",
                                parse_mode="HTML"
                            )
                except Exception as auth_err:
                    logger.warning("Could not notify author of expired test %s: %s", test.code, auth_err)

            await session.commit()
