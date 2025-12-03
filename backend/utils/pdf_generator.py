"""
PDF Generator Utility for Certificate Generation.

This module provides the PDFGenerator class for creating styled PDF certificates
for profitable test results. Uses ReportLab for PDF generation and includes
QR codes for verification.
"""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Optional

import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# Color Palette
BACKGROUND = HexColor("#0A0A0F")
ACCENT = HexColor("#00D4FF")
TEXT_PRIMARY = HexColor("#FFFFFF")
TEXT_SECONDARY = HexColor("#A1A1AA")
CARD_BG = HexColor("#18181B")

# Fonts
TITLE_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"
SMALL_FONT = "Helvetica"


class PDFGenerator:
    """
    PDF certificate generator with dark theme styling.
    
    Generates professional-looking certificates for profitable trading results
    with AlphaLab branding, metrics tables, and QR codes for verification.
    """
    
    def __init__(self):
        """Initialize PDF generator with page dimensions."""
        self.page_width, self.page_height = A4
        self.margin = 0.75 * inch
        
    def generate_certificate(
        self,
        agent_name: str,
        model: str,
        mode: str,
        test_type: str,
        asset: str,
        pnl_pct: Decimal,
        win_rate: Decimal,
        total_trades: int,
        max_drawdown_pct: Optional[Decimal],
        sharpe_ratio: Optional[Decimal],
        duration_display: str,
        test_period: str,
        verification_code: str,
        share_url: str,
        issued_at: datetime
    ) -> bytes:
        """
        Generate a certificate PDF with all metrics and styling.
        
        Args:
            agent_name: Name of the trading agent
            model: LLM model used
            mode: Agent mode (monk/omni)
            test_type: Type of test (backtest/forward)
            asset: Trading asset
            pnl_pct: Total PnL percentage
            win_rate: Win rate percentage
            total_trades: Number of trades
            max_drawdown_pct: Maximum drawdown percentage
            sharpe_ratio: Sharpe ratio
            duration_display: Human-readable duration
            test_period: Test period display string
            verification_code: Unique verification code
            share_url: Public verification URL
            issued_at: Certificate issuance timestamp
            
        Returns:
            PDF file as bytes
        """
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Draw all components
        self._draw_background(c)
        self._draw_header(c)
        self._draw_agent_section(c, agent_name, model, mode)
        self._draw_metrics_table(
            c,
            test_type,
            asset,
            pnl_pct,
            win_rate,
            total_trades,
            max_drawdown_pct,
            sharpe_ratio,
            duration_display,
            test_period
        )
        qr_image = self._generate_qr_code(share_url)
        self._draw_footer(c, verification_code, issued_at, qr_image)
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()

    def _draw_background(self, c: canvas.Canvas) -> None:
        """
        Draw the dark background for the certificate.
        
        Args:
            c: ReportLab canvas object
        """
        c.setFillColor(BACKGROUND)
        c.rect(0, 0, self.page_width, self.page_height, fill=True, stroke=False)
        
    def _draw_header(self, c: canvas.Canvas) -> None:
        """
        Draw the header section with AlphaLab branding.
        
        Args:
            c: ReportLab canvas object
        """
        # Title
        c.setFillColor(ACCENT)
        c.setFont(TITLE_FONT, 28)
        c.drawCentredString(self.page_width / 2, self.page_height - self.margin - 20, "AlphaLab")
        
        # Subtitle
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(BODY_FONT, 14)
        c.drawCentredString(self.page_width / 2, self.page_height - self.margin - 45, "Performance Certificate")
        
        # Decorative line
        c.setStrokeColor(ACCENT)
        c.setLineWidth(2)
        line_y = self.page_height - self.margin - 65
        c.line(self.margin + 100, line_y, self.page_width - self.margin - 100, line_y)
        
    def _draw_agent_section(
        self,
        c: canvas.Canvas,
        agent_name: str,
        model: str,
        mode: str
    ) -> None:
        """
        Draw the agent information section.
        
        Args:
            c: ReportLab canvas object
            agent_name: Name of the trading agent
            model: LLM model used
            mode: Agent mode (monk/omni)
        """
        y_position = self.page_height - self.margin - 120
        
        # Agent name (large, centered)
        c.setFillColor(TEXT_PRIMARY)
        c.setFont(TITLE_FONT, 32)
        c.drawCentredString(self.page_width / 2, y_position, agent_name)
        
        # Model and mode info
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(BODY_FONT, 12)
        info_text = f"{model} • {mode.upper()} Mode"
        c.drawCentredString(self.page_width / 2, y_position - 30, info_text)
        
    def _draw_metrics_table(
        self,
        c: canvas.Canvas,
        test_type: str,
        asset: str,
        pnl_pct: Decimal,
        win_rate: Decimal,
        total_trades: int,
        max_drawdown_pct: Optional[Decimal],
        sharpe_ratio: Optional[Decimal],
        duration_display: str,
        test_period: str
    ) -> None:
        """
        Draw the metrics table with performance data.
        
        Args:
            c: ReportLab canvas object
            test_type: Type of test (backtest/forward)
            asset: Trading asset
            pnl_pct: Total PnL percentage
            win_rate: Win rate percentage
            total_trades: Number of trades
            max_drawdown_pct: Maximum drawdown percentage
            sharpe_ratio: Sharpe ratio
            duration_display: Human-readable duration
            test_period: Test period display string
        """
        # Card background
        card_y = self.page_height - self.margin - 250
        card_height = 320
        card_width = self.page_width - 2 * self.margin
        
        c.setFillColor(CARD_BG)
        c.roundRect(
            self.margin,
            card_y - card_height,
            card_width,
            card_height,
            10,
            fill=True,
            stroke=False
        )
        
        # Section title
        c.setFillColor(ACCENT)
        c.setFont(TITLE_FONT, 16)
        c.drawString(self.margin + 20, card_y - 30, "Performance Metrics")
        
        # Test info
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(BODY_FONT, 11)
        test_info = f"{test_type.capitalize()} • {asset} • {test_period}"
        c.drawString(self.margin + 20, card_y - 50, test_info)
        
        # Metrics grid
        metrics_start_y = card_y - 85
        left_col_x = self.margin + 30
        right_col_x = self.page_width / 2 + 20
        row_height = 35
        
        # Format PnL with color
        pnl_color = HexColor("#10B981") if pnl_pct >= 0 else HexColor("#EF4444")
        pnl_text = f"+{pnl_pct:.2f}%" if pnl_pct >= 0 else f"{pnl_pct:.2f}%"
        
        # Left column metrics
        metrics_left = [
            ("Total PnL", pnl_text, pnl_color),
            ("Win Rate", f"{win_rate:.2f}%", TEXT_PRIMARY),
            ("Total Trades", str(total_trades), TEXT_PRIMARY),
            ("Duration", duration_display, TEXT_PRIMARY),
        ]
        
        for i, (label, value, color) in enumerate(metrics_left):
            y = metrics_start_y - (i * row_height)
            c.setFillColor(TEXT_SECONDARY)
            c.setFont(SMALL_FONT, 10)
            c.drawString(left_col_x, y, label)
            c.setFillColor(color)
            c.setFont(TITLE_FONT, 14)
            c.drawString(left_col_x, y - 18, value)
        
        # Right column metrics
        metrics_right = [
            ("Max Drawdown", f"{max_drawdown_pct:.2f}%" if max_drawdown_pct else "N/A", TEXT_PRIMARY),
            ("Sharpe Ratio", f"{sharpe_ratio:.3f}" if sharpe_ratio else "N/A", TEXT_PRIMARY),
        ]
        
        for i, (label, value, color) in enumerate(metrics_right):
            y = metrics_start_y - (i * row_height)
            c.setFillColor(TEXT_SECONDARY)
            c.setFont(SMALL_FONT, 10)
            c.drawString(right_col_x, y, label)
            c.setFillColor(color)
            c.setFont(TITLE_FONT, 14)
            c.drawString(right_col_x, y - 18, value)
        
    def _generate_qr_code(self, url: str) -> Image.Image:
        """
        Generate a QR code image for the verification URL.
        
        Args:
            url: URL to encode in QR code
            
        Returns:
            PIL Image object containing the QR code
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Create QR code with cyan color
        img = qr.make_image(fill_color="#00D4FF", back_color="#0A0A0F")
        return img
        
    def _draw_footer(
        self,
        c: canvas.Canvas,
        verification_code: str,
        issued_at: datetime,
        qr_image: Image.Image
    ) -> None:
        """
        Draw the footer with verification code and QR code.
        
        Args:
            c: ReportLab canvas object
            verification_code: Unique verification code
            issued_at: Certificate issuance timestamp
            qr_image: PIL Image object containing QR code
        """
        footer_y = self.margin + 80
        
        # Verification code (left side)
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(SMALL_FONT, 9)
        c.drawString(self.margin, footer_y + 40, "Verification Code:")
        
        c.setFillColor(ACCENT)
        c.setFont(TITLE_FONT, 14)
        c.drawString(self.margin, footer_y + 20, verification_code)
        
        # Issue date
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(SMALL_FONT, 9)
        issue_date_str = issued_at.strftime("%B %d, %Y")
        c.drawString(self.margin, footer_y, f"Issued: {issue_date_str}")
        
        # QR code (right side)
        qr_size = 1.2 * inch
        qr_x = self.page_width - self.margin - qr_size
        qr_y = footer_y - 10
        
        # Convert PIL image to ImageReader
        img_buffer = BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        img_reader = ImageReader(img_buffer)
        
        c.drawImage(img_reader, qr_x, qr_y, width=qr_size, height=qr_size)
        
        # QR code label
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(SMALL_FONT, 8)
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 15, "Scan to verify")
