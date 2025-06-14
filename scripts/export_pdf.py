#!/usr/bin/env python3
# ===================================================================
# scripts/export_pdf.py - PDF Report Generation Script
# ===================================================================

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.platypus import PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Task, User
from app.services.analytics_service import AnalyticsService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExporter:
    """Comprehensive PDF report generator"""
    
    def __init__(self):
        self.app = create_app()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1976d2'),
            alignment=1  # Center
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            textColor=colors.HexColor('#424242')
        )
        
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#1976d2')
        )
        
        # Body style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
    def generate_report(self, 
                       output_path: str,
                       report_type: str = 'summary',
                       date_from: datetime = None,
                       date_to: datetime = None,
                       filters: Dict[str, Any] = None) -> bool:
        """Generate PDF report"""
        
        try:
            with self.app.app_context():
                logger.info(f"Generating {report_type} PDF report: {output_path}")
                
                # Create document
                doc = SimpleDocTemplate(
                    output_path,
                    pagesize=A4,
                    rightMargin=inch,
                    leftMargin=inch,
                    topMargin=inch,
                    bottomMargin=inch
                )
                
                # Build story (content elements)
                story = []
                
                # Add header
                self._add_header(story)
                
                # Add content based on report type
                if report_type == 'summary':
                    self._add_summary_content(story, date_from, date_to, filters)
                elif report_type == 'detailed':
                    self._add_detailed_content(story, date_from, date_to, filters)
                elif report_type == 'analytics':
                    self._add_analytics_content(story, date_from, date_to, filters)
                elif report_type == 'tasks':
                    self._add_tasks_content(story, filters)
                else:
                    raise ValueError(f"Unknown report type: {report_type}")
                
                # Add footer
                self._add_footer(story)
                
                # Build PDF
                doc.build(story)
                
                logger.info(f"PDF report generated successfully: {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            return False
            
    def _add_header(self, story: List):
        """Add report header"""
        # Company logo (if available)
        logo_path = "static/images/logo.png"
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=2*inch, height=0.8*inch)
            story.append(logo)
            story.append(Spacer(1, 20))
            
        # Title
        title = Paragraph("Action Plan Management System", self.title_style)
        story.append(title)
        
        # Subtitle with date
        subtitle = Paragraph(f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", self.subtitle_style)
        story.append(subtitle)
        
        story.append(Spacer(1, 30))
        
    def _add_summary_content(self, story: List, date_from: datetime, date_to: datetime, filters: Dict):
        """Add summary report content"""
        # Get summary statistics
        analytics = AnalyticsService()
        stats = analytics.get_summary_stats(date_from, date_to)
        
        # Summary section
        story.append(Paragraph("📊 Résumé Exécutif", self.header_style))
        
        summary_data = [
            ['Métrique', 'Valeur'],
            ['Total des tâches', str(stats.get('total_tasks', 0))],
            ['Tâches terminées', str(stats.get('completed_tasks', 0))],
            ['Tâches en cours', str(stats.get('in_progress_tasks', 0))],
            ['Tâches en retard', str(stats.get('overdue_tasks', 0))],
            ['T