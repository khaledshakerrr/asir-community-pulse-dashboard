from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.data_cleaning import prepare_dashboard_data
from src.environmental_models import build_environmental_current_frame, build_environmental_forecast_frame
from src.google_sheets import load_dashboard_datasets
from src.official_analytics import build_executive_kpis
from src.source_registry import get_source_registry

OUTPUT_DIR = PROJECT_ROOT / "docs"
OUTPUT_PATH = OUTPUT_DIR / "asir_community_pulse_documentation_ar.pdf"
FONT_REGULAR = "ArabicRegular"
FONT_BOLD = "ArabicBold"


def rtl(text: str) -> str:
    return get_display(arabic_reshaper.reshape(str(text)))


def register_fonts() -> None:
    regular_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/tahoma.ttf"),
    ]
    bold_candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/tahomabd.ttf"),
    ]

    regular_font = next((path for path in regular_candidates if path.is_file()), None)
    bold_font = next((path for path in bold_candidates if path.is_file()), regular_font)

    if regular_font is None:
        raise FileNotFoundError("لم يتم العثور على خط عربي مناسب داخل نظام ويندوز لتوليد ملف PDF.")

    pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular_font)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_font or regular_font)))


def build_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ArabicTitle",
        parent=styles["Heading1"],
        fontName=FONT_BOLD,
        fontSize=22,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#102A43"),
        spaceAfter=14,
    )
    heading_style = ParagraphStyle(
        "ArabicHeading",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=15,
        leading=23,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#0B243D"),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ArabicBody",
        parent=styles["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=11,
        leading=20,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#102A43"),
        spaceAfter=6,
    )
    bullet_style = ParagraphStyle(
        "ArabicBullet",
        parent=body_style,
        leftIndent=0,
        rightIndent=0,
        bulletIndent=0,
    )
    small_style = ParagraphStyle(
        "ArabicSmall",
        parent=body_style,
        fontSize=9.5,
        leading=16,
        textColor=colors.HexColor("#486581"),
    )
    return title_style, heading_style, body_style, bullet_style, small_style


def paragraph(text: str, style) -> Paragraph:
    return Paragraph(rtl(text), style)


def bullet(text: str, style) -> Paragraph:
    return Paragraph(rtl(f"- {text}"), style)


def build_summary_examples() -> list[str]:
    try:
        datasets = prepare_dashboard_data(load_dashboard_datasets())
        executive_kpis = build_executive_kpis(datasets)
        environmental = build_environmental_current_frame(datasets, None)
        forecast = build_environmental_forecast_frame(datasets, None)
    except Exception as exc:
        return [f"تعذر إدراج أمثلة رقمية حية داخل الوثيقة وقت التوليد بسبب: {exc}"]

    examples: list[str] = []
    if executive_kpis:
        examples.append(f"مثال تنفيذي: {executive_kpis[0]['label']} = {executive_kpis[0]['value']}.")
    if not environmental.empty:
        top_respiratory = environmental.sort_values("respiratory_risk_index", ascending=False).iloc[0]
        examples.append(
            f"مثال بيئي حي: أعلى خطر تنفسي حاليًا في {top_respiratory['city_ar']} ضمن {top_respiratory['province_ar']} بقيمة {top_respiratory['respiratory_risk_index']:.1f}."
        )
    if not forecast.empty:
        top_forecast = forecast.sort_values("operational_pressure_forecast", ascending=False).iloc[0]
        examples.append(
            f"مثال تنبؤي: أعلى ضغط تشغيلي متوقع خلال 7 أيام يظهر في {top_forecast['city_ar']} بتاريخ {top_forecast['forecast_date']} بقيمة {top_forecast['operational_pressure_forecast']:.1f}."
        )
    return examples or ["لم تتوفر أمثلة رقمية إضافية في لحظة التوليد."]


def build_source_table_data():
    rows = [["المصدر", "الفئة", "الحالة", "الوصف"]]
    for item in get_source_registry():
        rows.append(
            [
                rtl(item["source_name"]),
                rtl(item["category"]),
                rtl(item["status"]),
                rtl(item["description"]),
            ]
        )
    return rows


def build_link_paragraph(url: str, style) -> Paragraph:
    safe_url = str(url).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    visible_url = "<br/>".join(simpleSplit(safe_url, style.fontName, style.fontSize, 410))
    return Paragraph(f'<link href="{safe_url}" color="#0B6E99">{visible_url}</link>', style)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    register_fonts()
    title_style, heading_style, body_style, bullet_style, small_style = build_styles()

    story = [
        paragraph("دليل منصة نبض المجتمع", title_style),
        paragraph(
            "وثيقة عربية تنفيذية تشرح الصفحات والمؤشرات والرسوم والمنهجية والمصادر المستخدمة داخل التطبيق.",
            body_style,
        ),
        Spacer(1, 0.35 * cm),
    ]

    sections = [
        (
            "1. الهدف التنفيذي",
            [
                "المنصة مصممة لدعم القرار الصحي والوقائي داخل المملكة العربية السعودية مع تركيز خاص على عسير والقصيم.",
                "القيمة الحقيقية للمنصة أنها نظام إنذار بيئي وصحي مبكر، وليست مجرد لوحة أرقام ثابتة.",
                "المنصة تربط بين البيانات الصحية الرسمية والطبقة السكانية والرصد البيئي الحي والتوقعات التشغيلية قصيرة المدى.",
            ],
        ),
        (
            "2. الصفحات داخل التطبيق",
            [
                "نظرة عامة: تعرض المؤشرات التنفيذية الرئيسية ومقارنة السعودية مع عسير والقصيم.",
                "الخريطة التفاعلية: تعرض التوزيع المكاني للمؤشرات الصحية والتنفيذية.",
                "المقارنة الإقليمية: تقارن البنية الصحية والوصول والجاهزية بين النطاقات الرئيسية.",
                "القوى العاملة والطاقة: تعرض الأطباء والتمريض والصيادلة ومزيج الخدمات.",
                "الخدمات والجودة: تعرض اتجاهات الطلب والجودة والجاهزية التشغيلية.",
                "البيئة والصحة: تربط الحرارة والرطوبة والرياح وجودة الهواء بالمشهد الصحي.",
                "المخاطر التنفسية: تعرض مؤشرات الخطر التنفسي والربو والإنفلونزا والالتهاب الرئوي بصورة استرشادية.",
                "الإنذار المبكر: تعرض أولويات التدخل والمدن الأعلى ضغطًا والمحفزات البيئية المؤثرة.",
                "التنبؤات: تعرض القراءة المستقبلية للضغط التشغيلي والمخاطر البيئية والتنفسية.",
                "المصادر والمنهجية: توثق كل مصدر مستخدم وتشرح الفروق بين البيانات الرسمية والمؤشرات المشتقة.",
            ],
        ),
        (
            "3. شرح المؤشرات التنفيذية الأساسية",
            [
                "إجمالي السكان: يوضح الحجم السكاني للنطاق المعروض بعد تطبيق المرشحات.",
                "مؤشر الجاهزية المركب: مؤشر مشتق يجمع القدرة الصحية والوصول والرضا وضغط التشغيل في قيمة تنفيذية موحدة.",
                "رضا وقت الطبيب: يعكس جودة التجربة الصحية من منظور الوقت والرضا.",
                "عدد المستشفيات: يعرض الطاقة الصحية الأساسية في النطاق المحدد.",
                "متوسط وقت الانتظار: يمثل ضغطًا تشغيليًا معياريًا مبنيًا على البيانات المتاحة داخل النسخة الحالية.",
                "مناطق الأولوية: توضح عدد المناطق التي تحتاج تدخلًا أعلى من منظور الجاهزية أو المخاطر.",
            ],
        ),
        (
            "4. شرح مؤشرات البيئة والصحة",
            [
                "مؤشر جودة الهواء: يقيس ضغط جودة الهواء اعتمادًا على AQI وPM2.5 وPM10 وبعض الغازات المؤثرة.",
                "مؤشر الإجهاد الحراري: يقيس أثر الحرارة والرطوبة والرياح والأشعة فوق البنفسجية على الضغط الحراري.",
                "مؤشر أثر الغبار: يركز على أثر الغبار والجسيمات وسرعة الرياح على الحساسية والصحة التنفسية.",
                "مؤشر الصحة البيئية: يجمع جودة الهواء والحرارة والغبار والعوامل البيئية في قراءة تنفيذية موحدة.",
            ],
        ),
        (
            "5. شرح مؤشرات المخاطر التنفسية",
            [
                "مؤشر الخطر التنفسي: قراءة مركبة تعكس الضغط التنفسي النسبي، وليس عددًا سريريًا مباشرًا للمرضى.",
                "مؤشر خطر الربو: يركز على العوامل الأكثر ارتباطًا بتهييج الربو والحساسية التنفسية.",
                "مؤشر خطر الإنفلونزا: مؤشر استرشادي موسمي يربط الحرارة والرطوبة وبعض العوامل المساعدة على النشاط الموسمي.",
                "مؤشر خطر الالتهاب الرئوي: يعكس الضغط التنفسي الأشد لدى المدن الأعلى حساسية للهواء والعبء المزمن.",
            ],
        ),
        (
            "6. شرح الرسوم البيانية باختصار عملي",
            [
                "الرسوم الشريطية الأفقية تستخدم لترتيب المناطق أو المدن وإبراز الأعلى والأدنى بوضوح تنفيذي.",
                "الرسوم الخطية تعرض الاتجاه عبر الزمن وتساعد في قراءة التحسن أو التصاعد أو الإنذار المبكر.",
                "الخرائط التفاعلية تعرض الفروق المكانية مع إمكانية التكبير والتصغير وقراءة التلميحات لكل مدينة.",
                "الخرائط الحرارية الأسبوعية تساعد على رؤية تغير الخطر يومًا بيوم لكل مدينة بشكل سريع جدًا.",
            ],
        ),
        (
            "7. معنى التنبؤات الحالية",
            [
                "التنبؤات الحالية داخل المشروع هي تنبؤات تشغيلية واستباقية للمخاطر والضغط، وليست تشخيصًا سريريًا مباشرًا لعدد المرضى.",
                "القيمة التنفيذية هنا تتمثل في الإنذار المبكر وتحديد الأولويات قبل ارتفاع الضغط الفعلي على الخدمة.",
                "كلما توفرت سلاسل زمنية رسمية للحالات أو الطوارئ أو الأمراض الموسمية، يمكن رفع دقة النماذج المرضية مستقبلًا.",
            ],
        ),
        (
            "8. أمثلة عملية للشرح أمام العميلة",
            build_summary_examples(),
        ),
        (
            "9. ما الذي تبيعه المنصة فعليًا",
            [
                "المنصة تُباع بوصفها نظام إنذار بيئي وصحي مبكر.",
                "الرسالة الأقوى هي: ربط الطقس والهواء والعبء الصحي والبيانات الرسمية لاكتشاف أين قد يرتفع الخطر قبل تفاقمه.",
                "المخرجات البيعية الأقوى هي: مؤشرات مخاطر، خرائط، تنبؤات، تنبيهات، وأولويات تنفيذية قابلة للعرض.",
            ],
        ),
        (
            "10. القيود العلمية والمنهجية",
            [
                "بعض المؤشرات الحالية مشتقة تحليليًا وليست منشورة بنفس الاسم من الجهة الرسمية.",
                "طبقة الرصد البيئي الحالية تعتمد على بيانات حية عامة وموثقة، لكنها لا تغني عن قواعد الحالات السريرية التفصيلية إذا كان المطلوب تنبؤًا مرضيًا سريريًا عالي الدقة.",
                "النسخة الحالية مناسبة جدًا للعرض التنفيذي والبيع كنظام إنذار مبكر وتحليل قطاعي، وليست بديلًا عن منصة ترصد سريري ميداني داخل المستشفيات.",
            ],
        ),
    ]

    for heading, bullets in sections:
        story.append(paragraph(heading, heading_style))
        for item in bullets:
            story.append(bullet(item, bullet_style))
        story.append(Spacer(1, 0.18 * cm))

    story.append(paragraph("11. قائمة المصادر المستخدمة", heading_style))
    source_table = Table(build_source_table_data(), repeatRows=1, colWidths=[4.6 * cm, 2.7 * cm, 2.5 * cm, 7.2 * cm])
    source_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9F2EE")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102A43")),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E2EC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FBFC")]),
                ("LEADING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(source_table)
    story.append(Spacer(1, 0.25 * cm))

    story.append(paragraph("12. روابط المصادر المباشرة", heading_style))
    link_style = ParagraphStyle("LinkStyle", parent=small_style, alignment=TA_RIGHT, fontName=FONT_REGULAR)
    for item in get_source_registry():
        story.append(paragraph(item["source_name"], body_style))
        story.append(build_link_paragraph(item["url"], link_style))
        story.append(Spacer(1, 0.08 * cm))

    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.3 * cm,
        title="Asir Community Pulse Documentation",
        author="Codex",
    )
    document.build(story)
    print(f"Generated PDF: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
