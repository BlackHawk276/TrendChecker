"""
Email service for sending verification, password reset, and notification emails.
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from jinja2 import Template

from app.config import settings


class EmailService:
    """
    Email service for sending transactional emails.
    """

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Optional plain text content

        Returns:
            True if email sent successfully

        Raises:
            Exception: If email sending fails
        """
        if not settings.smtp_user or not settings.smtp_password:
            print("⚠️ SMTP credentials not configured. Email not sent.")
            print(f"Would send to: {to_email}")
            print(f"Subject: {subject}")
            return False

        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = settings.email_from
        message["To"] = to_email
        message["Subject"] = subject

        # Add plain text and HTML parts
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)

        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        try:
            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                start_tls=True,
            )
            return True
        except Exception as e:
            print(f"Failed to send email to {to_email}: {str(e)}")
            raise

    @staticmethod
    def _render_template(template_str: str, **kwargs) -> str:
        """
        Render Jinja2 template with context.

        Args:
            template_str: Template string
            **kwargs: Template context variables

        Returns:
            Rendered template string
        """
        template = Template(template_str)
        return template.render(**kwargs)

    @classmethod
    async def send_verification_email(
        cls,
        to_email: str,
        full_name: str,
        verification_token: str,
        frontend_url: str = "http://localhost:3000"
    ) -> bool:
        """
        Send email verification email.

        Args:
            to_email: User's email address
            full_name: User's full name
            verification_token: Verification token
            frontend_url: Frontend application URL

        Returns:
            True if email sent successfully
        """
        verification_link = f"{frontend_url}/verify-email?token={verification_token}"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #4F46E5; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
                .content { background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }
                .button { display: inline-block; padding: 12px 30px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ app_name }}</h1>
                </div>
                <div class="content">
                    <h2>Welcome, {{ full_name }}!</h2>
                    <p>Thank you for registering with {{ app_name }}. Please verify your email address to activate your account.</p>
                    <p>Click the button below to verify your email:</p>
                    <p style="text-align: center;">
                        <a href="{{ verification_link }}" class="button">Verify Email Address</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #4F46E5;">{{ verification_link }}</p>
                    <p><strong>This link will expire in 24 hours.</strong></p>
                    <p>If you didn't create an account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html_content = cls._render_template(
            html_template,
            app_name=settings.app_name,
            full_name=full_name,
            verification_link=verification_link
        )

        text_content = f"""
        Welcome to {settings.app_name}, {full_name}!

        Please verify your email address by visiting this link:
        {verification_link}

        This link will expire in 24 hours.

        If you didn't create an account, please ignore this email.
        """

        return await cls.send_email(
            to_email=to_email,
            subject=f"Verify your {settings.app_name} account",
            html_content=html_content,
            text_content=text_content
        )

    @classmethod
    async def send_password_reset_email(
        cls,
        to_email: str,
        full_name: str,
        reset_token: str,
        frontend_url: str = "http://localhost:3000"
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: User's email address
            full_name: User's full name
            reset_token: Password reset token
            frontend_url: Frontend application URL

        Returns:
            True if email sent successfully
        """
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"

        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #DC2626; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
                .content { background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }
                .button { display: inline-block; padding: 12px 30px; background-color: #DC2626; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #666; }
                .warning { background-color: #FEF2F2; border-left: 4px solid #DC2626; padding: 15px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset</h1>
                </div>
                <div class="content">
                    <h2>Hello, {{ full_name }}</h2>
                    <p>We received a request to reset your password for your {{ app_name }} account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{{ reset_link }}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #DC2626;">{{ reset_link }}</p>
                    <div class="warning">
                        <p><strong>⚠️ Important:</strong></p>
                        <ul>
                            <li>This link will expire in 1 hour</li>
                            <li>If you didn't request a password reset, please ignore this email</li>
                            <li>Your password will not change unless you click the link above</li>
                        </ul>
                    </div>
                </div>
                <div class="footer">
                    <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html_content = cls._render_template(
            html_template,
            app_name=settings.app_name,
            full_name=full_name,
            reset_link=reset_link
        )

        text_content = f"""
        Hello {full_name},

        We received a request to reset your password for your {settings.app_name} account.

        Please visit this link to reset your password:
        {reset_link}

        This link will expire in 1 hour.

        If you didn't request a password reset, please ignore this email.
        Your password will not change unless you click the link above.
        """

        return await cls.send_email(
            to_email=to_email,
            subject=f"Reset your {settings.app_name} password",
            html_content=html_content,
            text_content=text_content
        )

    @classmethod
    async def send_password_changed_email(
        cls,
        to_email: str,
        full_name: str
    ) -> bool:
        """
        Send password changed confirmation email.

        Args:
            to_email: User's email address
            full_name: User's full name

        Returns:
            True if email sent successfully
        """
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #10B981; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }
                .content { background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }
                .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✓ Password Changed</h1>
                </div>
                <div class="content">
                    <h2>Hello, {{ full_name }}</h2>
                    <p>Your {{ app_name }} password has been successfully changed.</p>
                    <p>If you didn't make this change, please contact our support team immediately.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 {{ app_name }}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        html_content = cls._render_template(
            html_template,
            app_name=settings.app_name,
            full_name=full_name
        )

        text_content = f"""
        Hello {full_name},

        Your {settings.app_name} password has been successfully changed.

        If you didn't make this change, please contact our support team immediately.
        """

        return await cls.send_email(
            to_email=to_email,
            subject=f"Your {settings.app_name} password has been changed",
            html_content=html_content,
            text_content=text_content
        )


# Singleton instance
email_service = EmailService()
