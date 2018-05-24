from django.utils.translation import ugettext_lazy as _
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table,\
    TableStyle, Image
import StringIO
import PIL
import urllib2


from serverapi.models import ExpenseDocument
from django.conf import settings

class PdfGenerate:
    # initialize class
    def __init__(self, buffer, pageSize):
        self.buffer = buffer
        # default format is A4
        if pageSize == 'A4':
            self.pageSize = A4
        elif pageSize == 'Letter':
            self.pageSize = letter
        self.width, self.height = self.pageSize

    def pageNumber(self, canvas, doc):
        number = canvas.getPageNumber()
        canvas.drawCentredString(100*mm, 15*mm, str(number))


    def report(self, roadshow_expenses, title, request):
        # set some characteristics for pdf document
        doc = SimpleDocTemplate(
            self.buffer,
            rightMargin=72,
            leftMargin=72,
            topMargin=30,
            bottomMargin=72,
            pagesize=self.pageSize
        )
        # a collection of styles offer by the library
        styles = getSampleStyleSheet()
        # add custom paragraph style
        styles.add(
            ParagraphStyle(
                name="TableHeader",
                fontSize=11,
                alignment=TA_CENTER,
            )
        )
        styles.add(
            ParagraphStyle(
                name="ParagraphTitle",
                fontSize=11,
                alignment=TA_JUSTIFY,
            )
        )
        styles.add(
            ParagraphStyle(
                name="Justify",
                alignment=TA_JUSTIFY,
            )
        )
        # list used for elements added into document
        data = []
        data.append(Paragraph(title, styles['Title']))
        # insert a blank space
        data.append(Spacer(1, 12))
        table_data = []
        # table header
        table_data.append([
            Paragraph('Date', styles['TableHeader']),
            Paragraph('Category', styles['TableHeader']),
            Paragraph('Payment Method', styles['TableHeader']),
            Paragraph('Description', styles['TableHeader']),
            Paragraph('Amount', styles['TableHeader']),
        ])
        for expense in roadshow_expenses:
            table_data.append(
                [
                    expense.expense_date,
                    expense.category.name,
                    expense.payment_method,
                    expense.expense_notes,
                    u"{0} $".format(expense.final_amount),
                ]
            )
        # create table
        wh_table = Table(table_data, colWidths=[doc.width/7.0]*7)
        wh_table.hAlign = 'LEFT'
        wh_table.setStyle(
            TableStyle(
                [
                 ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                 ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
                 ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                 ('BACKGROUND', (0, 0), (-1, 0), colors.gray)
                ]
            )
        )
        data.append(wh_table)
        data.append(Spacer(1, 48))

        for expense in roadshow_expenses:
            docs = ExpenseDocument.objects.filter(expense=expense)
            if docs:
                data.append(Paragraph("{0} bills".format(expense.expense_date), styles['Title']))
                for document in docs:
                    image_url = request.build_absolute_uri(
                        "{0}/{1}".format(settings.MEDIA_URL, document.docfile)
                    )
                    try:
                        from reportlab.lib.units import inch
                        I = Image(
                            "{0}/{1}".format(settings.BASE_DIR, document.docfile),
                            width=3*inch,
                            height=3*inch
                        )
                        data.append(I)
                    except:
                        pass

        # create document
        doc.build(
            data,
            onFirstPage=self.pageNumber,
            onLaterPages=self.pageNumber
        )
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf
