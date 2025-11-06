"""
Notification Service

Handles alert notifications and email delivery for:
- New store alerts
- Price drop alerts
- Trending score alerts
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.store import Store
from app.models.alert import Alert, AlertType
from app.services.email_service import EmailService
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for processing and sending alert notifications.
    """

    @staticmethod
    async def process_new_store_alerts(store: Store, db: AsyncSession) -> int:
        """
        Process new store alerts for users who match criteria.

        Args:
            store: Newly added store
            db: Database session

        Returns:
            Number of notifications sent
        """
        notifications_sent = 0

        try:
            # Get all active new_store alerts
            stmt = select(Alert, User).join(User).where(
                and_(
                    Alert.alert_type == AlertType.NEW_STORE,
                    Alert.is_active == True,
                    User.is_active == True,
                    User.is_verified == True
                )
            )

            result = await db.execute(stmt)
            alerts_and_users = result.all()

            for alert, user in alerts_and_users:
                # Check if store matches alert criteria
                if NotificationService._matches_criteria(store, alert.criteria):
                    # Send notification
                    await NotificationService.send_new_store_notification(
                        user=user,
                        store=store,
                        alert=alert
                    )
                    notifications_sent += 1

            logger.info(f"Sent {notifications_sent} new store notifications for {store.domain}")

        except Exception as e:
            logger.error(f"Error processing new store alerts: {str(e)}")

        return notifications_sent

    @staticmethod
    async def process_price_drop_alerts(
        store: Store,
        product_id: UUID,
        old_price: float,
        new_price: float,
        db: AsyncSession
    ) -> int:
        """
        Process price drop alerts for a specific product.

        Args:
            store: Store containing the product
            product_id: Product UUID
            old_price: Previous price
            new_price: New price
            db: Database session

        Returns:
            Number of notifications sent
        """
        notifications_sent = 0

        try:
            # Get all active price_drop alerts for this store
            stmt = select(Alert, User).join(User).where(
                and_(
                    Alert.alert_type == AlertType.PRICE_DROP,
                    Alert.store_id == store.id,
                    Alert.is_active == True,
                    User.is_active == True,
                    User.is_verified == True
                )
            )

            result = await db.execute(stmt)
            alerts_and_users = result.all()

            # Calculate price drop percentage
            drop_percentage = ((old_price - new_price) / old_price) * 100

            for alert, user in alerts_and_users:
                # Check if drop meets criteria
                min_drop = alert.criteria.get("min_drop_percentage", 10) if alert.criteria else 10

                if drop_percentage >= min_drop:
                    # Send notification
                    await NotificationService.send_price_drop_notification(
                        user=user,
                        store=store,
                        product_id=product_id,
                        old_price=old_price,
                        new_price=new_price,
                        drop_percentage=drop_percentage
                    )
                    notifications_sent += 1

            logger.info(f"Sent {notifications_sent} price drop notifications for store {store.domain}")

        except Exception as e:
            logger.error(f"Error processing price drop alerts: {str(e)}")

        return notifications_sent

    @staticmethod
    async def process_trending_alerts(
        store: Store,
        old_score: float,
        new_score: float,
        db: AsyncSession
    ) -> int:
        """
        Process trending score alerts for a store.

        Args:
            store: Store with updated trending score
            old_score: Previous trending score
            new_score: New trending score
            db: Database session

        Returns:
            Number of notifications sent
        """
        notifications_sent = 0

        try:
            # Get all active trending alerts for this store
            stmt = select(Alert, User).join(User).where(
                and_(
                    Alert.alert_type == AlertType("trending"),  # Custom alert type
                    Alert.store_id == store.id,
                    Alert.is_active == True,
                    User.is_active == True,
                    User.is_verified == True
                )
            )

            result = await db.execute(stmt)
            alerts_and_users = result.all()

            # Calculate score increase
            score_increase = new_score - old_score

            for alert, user in alerts_and_users:
                # Check if increase meets criteria
                min_increase = alert.criteria.get("min_score_increase", 10) if alert.criteria else 10

                if score_increase >= min_increase:
                    # Send notification
                    await NotificationService.send_trending_notification(
                        user=user,
                        store=store,
                        old_score=old_score,
                        new_score=new_score,
                        score_increase=score_increase
                    )
                    notifications_sent += 1

            logger.info(f"Sent {notifications_sent} trending notifications for store {store.domain}")

        except Exception as e:
            logger.error(f"Error processing trending alerts: {str(e)}")

        return notifications_sent

    @staticmethod
    def _matches_criteria(store: Store, criteria: Optional[Dict]) -> bool:
        """
        Check if a store matches alert criteria.

        Args:
            store: Store to check
            criteria: Alert criteria dict

        Returns:
            True if store matches criteria
        """
        if not criteria:
            return True

        # Check category
        if "category" in criteria:
            if store.category.value != criteria["category"]:
                return False

        # Check minimum products
        if "min_products" in criteria:
            if store.product_count < criteria["min_products"]:
                return False

        # Check minimum trending score
        if "min_trending_score" in criteria:
            if store.trending_score < criteria["min_trending_score"]:
                return False

        # Check keywords in store name/description
        if "keywords" in criteria and criteria["keywords"]:
            keywords = [kw.lower() for kw in criteria["keywords"]]
            store_text = f"{store.name} {store.description or ''}".lower()

            if not any(keyword in store_text for keyword in keywords):
                return False

        return True

    @staticmethod
    async def send_new_store_notification(
        user: User,
        store: Store,
        alert: Alert
    ) -> bool:
        """
        Send new store notification email.

        Args:
            user: User to notify
            store: New store
            alert: Alert configuration

        Returns:
            True if sent successfully
        """
        try:
            # Check if we've already sent this notification (prevent duplicates)
            cache_key = f"notification_sent:{alert.id}:{store.id}"
            redis_client = await RedisService.get_redis()

            if await redis_client.exists(cache_key):
                logger.info(f"Notification already sent for alert {alert.id} and store {store.id}")
                return False

            # Send email
            subject = f"🔥 New {store.category.value.title()} Store Discovered: {store.name}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .store-card {{ background: white; padding: 20px; border-radius: 8px;
                                  margin: 20px 0; border-left: 4px solid #667eea; }}
                    .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                    .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                    .metric-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                    .button {{ display: inline-block; padding: 12px 30px; background: #667eea;
                             color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 New Store Alert!</h1>
                        <p>A new store matching your criteria has been discovered</p>
                    </div>
                    <div class="content">
                        <div class="store-card">
                            <h2>{store.name}</h2>
                            <p><strong>Domain:</strong> {store.domain}</p>
                            <p><strong>Category:</strong> {store.category.value.title()}</p>

                            {f'<p><strong>Description:</strong> {store.description}</p>' if store.description else ''}

                            <div style="margin: 20px 0;">
                                <div class="metric">
                                    <div class="metric-label">Trending Score</div>
                                    <div class="metric-value">{store.trending_score:.1f}</div>
                                </div>
                                <div class="metric">
                                    <div class="metric-label">Products</div>
                                    <div class="metric-value">{store.product_count}</div>
                                </div>
                                {f'<div class="metric"><div class="metric-label">Avg Price</div><div class="metric-value">${store.avg_product_price:.2f}</div></div>' if store.avg_product_price else ''}
                            </div>

                            <a href="https://app.example.com/stores/{store.id}" class="button">
                                View Store Details →
                            </a>
                        </div>

                        <p style="color: #666; font-size: 14px;">
                            This alert was triggered by your "{alert.alert_type.value}" alert configuration.
                            You can manage your alerts in your account settings.
                        </p>
                    </div>
                    <div class="footer">
                        <p>You're receiving this because you set up an alert in E-Commerce Intelligence SaaS</p>
                        <p><a href="https://app.example.com/settings/alerts">Manage Alerts</a> |
                           <a href="https://app.example.com/settings/notifications">Notification Settings</a></p>
                    </div>
                </div>
            </body>
            </html>
            """

            success = await EmailService.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                from_name="E-Commerce Intelligence"
            )

            if success:
                # Mark as sent (cache for 7 days)
                await redis_client.setex(cache_key, 604800, "1")
                logger.info(f"Sent new store notification to {user.email} for {store.domain}")

            return success

        except Exception as e:
            logger.error(f"Error sending new store notification: {str(e)}")
            return False

    @staticmethod
    async def send_price_drop_notification(
        user: User,
        store: Store,
        product_id: UUID,
        old_price: float,
        new_price: float,
        drop_percentage: float
    ) -> bool:
        """
        Send price drop notification email.

        Args:
            user: User to notify
            store: Store containing product
            product_id: Product UUID
            old_price: Previous price
            new_price: New price
            drop_percentage: Price drop percentage

        Returns:
            True if sent successfully
        """
        try:
            subject = f"💰 Price Drop Alert: {drop_percentage:.0f}% off at {store.name}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                              color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .price-card {{ background: white; padding: 20px; border-radius: 8px;
                                  margin: 20px 0; text-align: center; }}
                    .old-price {{ text-decoration: line-through; color: #999; font-size: 18px; }}
                    .new-price {{ font-size: 36px; font-weight: bold; color: #f5576c; margin: 10px 0; }}
                    .savings {{ background: #4ade80; color: white; padding: 10px 20px;
                              border-radius: 20px; display: inline-block; font-weight: bold; }}
                    .button {{ display: inline-block; padding: 12px 30px; background: #f5576c;
                             color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>💰 Price Drop Alert!</h1>
                        <p>A product you're watching just got cheaper</p>
                    </div>
                    <div class="content">
                        <div class="price-card">
                            <h2>{store.name}</h2>

                            <div class="old-price">${old_price:.2f}</div>
                            <div class="new-price">${new_price:.2f}</div>
                            <div class="savings">Save {drop_percentage:.0f}% (${old_price - new_price:.2f})</div>

                            <a href="https://app.example.com/products/{product_id}" class="button">
                                View Product →
                            </a>
                        </div>

                        <p style="text-align: center; color: #666;">
                            ⏰ Price drops don't last forever - act fast!
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            return await EmailService.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                from_name="E-Commerce Intelligence"
            )

        except Exception as e:
            logger.error(f"Error sending price drop notification: {str(e)}")
            return False

    @staticmethod
    async def send_trending_notification(
        user: User,
        store: Store,
        old_score: float,
        new_score: float,
        score_increase: float
    ) -> bool:
        """
        Send trending score increase notification.

        Args:
            user: User to notify
            store: Store with updated score
            old_score: Previous score
            new_score: New score
            score_increase: Score increase

        Returns:
            True if sent successfully
        """
        try:
            subject = f"📈 Trending Up: {store.name} Score +{score_increase:.1f}"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                              color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .score-card {{ background: white; padding: 20px; border-radius: 8px;
                                  margin: 20px 0; text-align: center; }}
                    .score {{ font-size: 48px; font-weight: bold; color: #43e97b; }}
                    .increase {{ color: #43e97b; font-size: 24px; font-weight: bold; }}
                    .button {{ display: inline-block; padding: 12px 30px; background: #43e97b;
                             color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📈 Store Trending Up!</h1>
                        <p>A store you're watching is gaining momentum</p>
                    </div>
                    <div class="content">
                        <div class="score-card">
                            <h2>{store.name}</h2>
                            <p>{store.domain}</p>

                            <div class="score">{new_score:.1f}</div>
                            <div class="increase">↑ +{score_increase:.1f} points</div>

                            <p style="color: #666; margin: 20px 0;">
                                Previous score: {old_score:.1f}
                            </p>

                            <a href="https://app.example.com/stores/{store.id}" class="button">
                                View Analytics →
                            </a>
                        </div>

                        <p style="text-align: center; color: #666;">
                            🔥 This store is getting hot - check out what's driving the trend!
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            return await EmailService.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                from_name="E-Commerce Intelligence"
            )

        except Exception as e:
            logger.error(f"Error sending trending notification: {str(e)}")
            return False

    @staticmethod
    async def test_notification(user: User, notification_type: str = "new_store") -> bool:
        """
        Send a test notification to verify email configuration.

        Args:
            user: User to send test to
            notification_type: Type of test notification

        Returns:
            True if sent successfully
        """
        try:
            subject = "🧪 Test Notification - E-Commerce Intelligence SaaS"

            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #667eea; color: white; padding: 30px; text-align: center; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✅ Test Notification</h1>
                        <p>Your notifications are working correctly!</p>
                    </div>
                    <div style="padding: 20px;">
                        <p>This is a test notification to verify that your email alerts are set up properly.</p>
                        <p>You will receive alerts when:</p>
                        <ul>
                            <li>New stores matching your criteria are discovered</li>
                            <li>Products in your saved stores drop in price</li>
                            <li>Your saved stores increase in trending score</li>
                        </ul>
                        <p>Manage your alerts in your account settings.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            return await EmailService.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content,
                from_name="E-Commerce Intelligence"
            )

        except Exception as e:
            logger.error(f"Error sending test notification: {str(e)}")
            return False
