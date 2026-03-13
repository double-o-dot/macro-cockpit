"""
젠슨 황 AI 인프라 투자 전망 보고서 PDF 생성
2026-03-11 작성 | Fortune, Motley Fool, NVIDIA GTC 2026 등 종합
"""

from fpdf import FPDF
import os
from datetime import datetime


class JensenHuangReportPDF(FPDF):
    CREAM = (253, 249, 242)
    DARK = (51, 51, 51)
    TERRACOTTA = (180, 90, 60)
    NVIDIA_GREEN = (118, 185, 0)
    LIGHT_GRAY = (240, 237, 230)
    WHITE = (255, 255, 255)
    MUTED = (120, 110, 100)

    def __init__(self):
        super().__init__()
        font_path = "C:/Windows/Fonts/"
        self.add_font("Malgun", "", os.path.join(font_path, "malgun.ttf"))
        self.add_font("Malgun", "B", os.path.join(font_path, "malgunbd.ttf"))
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_fill_color(*self.TERRACOTTA)
        self.rect(0, 0, 210, 4, "F")
        if self.page_no() > 1:
            self.set_font("Malgun", "B", 8)
            self.set_text_color(*self.MUTED)
            self.set_y(8)
            self.cell(0, 5, "Jensen Huang AI Infrastructure Report | 2026.03", align="R")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Malgun", "", 7)
        self.set_text_color(*self.MUTED)
        self.cell(0, 10, f"- {self.page_no()} -", align="C")

    def cover_page(self):
        self.add_page()
        self.set_fill_color(*self.CREAM)
        self.rect(0, 0, 210, 297, "F")

        self.ln(45)

        # NVIDIA accent stripe
        self.set_fill_color(*self.NVIDIA_GREEN)
        self.rect(20, self.get_y(), 170, 2, "F")
        self.ln(15)

        # Title
        self.set_font("Malgun", "B", 26)
        self.set_text_color(*self.DARK)
        self.cell(0, 14, "젠슨 황(Jensen Huang)", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.cell(0, 14, "AI 인프라 투자 전망", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        # Accent line
        x_center = 105
        self.set_draw_color(*self.TERRACOTTA)
        self.set_line_width(1.2)
        self.line(x_center - 35, self.get_y(), x_center + 35, self.get_y())
        self.ln(10)

        # Subtitle
        self.set_font("Malgun", "", 14)
        self.set_text_color(*self.MUTED)
        self.cell(0, 10, '"$700B는 시작일 뿐, 수조 달러가 더 필요하다"', align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(6)

        self.set_font("Malgun", "", 11)
        self.set_text_color(*self.TERRACOTTA)
        self.cell(0, 8, "GTC 2026 특별 보고서", align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(40)

        # Date & Info
        self.set_font("Malgun", "", 10)
        self.set_text_color(*self.MUTED)
        self.cell(0, 7, f"작성일: {datetime.now().strftime('%Y년 %m월 %d일')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 7, "출처: Fortune, Motley Fool, NVIDIA Newsroom, ainvest, 한국경제, 글로벌이코노믹", align="C", new_x="LMARGIN", new_y="NEXT")

        # Bottom accent bar
        self.set_fill_color(*self.NVIDIA_GREEN)
        self.rect(0, 293, 210, 4, "F")

    def new_page(self):
        self.add_page()
        self.set_fill_color(*self.CREAM)
        self.rect(0, 0, 210, 297, "F")

    def section_title(self, title, number=None):
        self.ln(6)
        self.set_fill_color(*self.TERRACOTTA)
        self.rect(10, self.get_y(), 3, 10, "F")
        self.set_font("Malgun", "B", 14)
        self.set_text_color(*self.DARK)
        prefix = f"{number}. " if number else ""
        self.set_x(17)
        self.cell(0, 10, f"{prefix}{title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def sub_title(self, title):
        self.set_font("Malgun", "B", 11)
        self.set_text_color(*self.TERRACOTTA)
        self.set_x(15)
        self.cell(0, 8, f">> {title}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Malgun", "", 10)
        self.set_text_color(*self.DARK)
        self.set_x(15)
        self.multi_cell(180, 6.5, text)
        self.ln(2)

    def bullet(self, text, indent=15):
        self.set_font("Malgun", "", 10)
        self.set_text_color(*self.DARK)
        self.set_x(indent)
        self.cell(5, 6.5, chr(8226))
        self.set_x(indent + 5)
        self.multi_cell(170, 6.5, text)
        self.ln(1)

    def quote_box(self, text, speaker=""):
        y = self.get_y()
        self.set_fill_color(245, 240, 230)
        self.set_x(15)
        # Calculate height needed
        self.set_font("Malgun", "", 10)
        lines = len(text) / 55 + 1
        box_h = max(lines * 7 + 14, 24)
        self.rect(15, y, 180, box_h, "F")

        # Left accent bar
        self.set_fill_color(*self.TERRACOTTA)
        self.rect(15, y, 3, box_h, "F")

        # Quote mark
        self.set_font("Malgun", "B", 20)
        self.set_text_color(*self.TERRACOTTA)
        self.set_xy(21, y)
        self.cell(10, 10, chr(8220))

        # Quote text
        self.set_font("Malgun", "", 10)
        self.set_text_color(*self.DARK)
        self.set_xy(22, y + 8)
        self.multi_cell(168, 6.5, text)

        if speaker:
            self.set_font("Malgun", "B", 9)
            self.set_text_color(*self.MUTED)
            self.set_x(22)
            self.cell(0, 6, f"- {speaker}")

        self.set_y(y + box_h + 4)

    def key_stat_box(self, label, value, desc=""):
        y = self.get_y()
        self.set_fill_color(*self.LIGHT_GRAY)
        box_h = 22 if not desc else 28
        self.rect(15, y, 180, box_h, "F")

        self.set_font("Malgun", "B", 18)
        self.set_text_color(*self.TERRACOTTA)
        self.set_xy(20, y + 2)
        self.cell(55, 10, value)

        self.set_font("Malgun", "B", 10)
        self.set_text_color(*self.DARK)
        self.set_xy(75, y + 3)
        self.cell(115, 8, label)

        if desc:
            self.set_font("Malgun", "", 8)
            self.set_text_color(*self.MUTED)
            self.set_xy(75, y + 12)
            self.cell(115, 6, desc)

        self.set_y(y + box_h + 4)

    def table_row(self, cells, is_header=False, col_widths=None):
        if col_widths is None:
            col_widths = [60, 60, 70]
        if is_header:
            self.set_fill_color(*self.TERRACOTTA)
            self.set_text_color(*self.WHITE)
            self.set_font("Malgun", "B", 10)
        else:
            self.set_fill_color(*self.LIGHT_GRAY)
            self.set_text_color(*self.DARK)
            self.set_font("Malgun", "", 9)
        x_start = (210 - sum(col_widths)) / 2
        self.set_x(x_start)
        for i, cell_text in enumerate(cells):
            self.cell(col_widths[i], 9, cell_text, border=0, fill=True, align="C")
        self.ln()
        if not is_header:
            self.set_draw_color(*self.CREAM)
            self.set_line_width(0.3)
            self.line(x_start, self.get_y(), x_start + sum(col_widths), self.get_y())

    def source_item(self, name, url):
        self.set_font("Malgun", "B", 8)
        self.set_text_color(*self.TERRACOTTA)
        self.set_x(15)
        self.cell(5, 5, chr(8226))
        self.set_x(20)
        self.cell(0, 5, name, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Malgun", "", 7)
        self.set_text_color(*self.MUTED)
        self.set_x(20)
        self.cell(0, 4, url, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)


def generate_report():
    pdf = JensenHuangReportPDF()

    # ── Cover ──
    pdf.cover_page()

    # ══════════════════════════════════════════════════════════
    # Page 2: 핵심 요약 + 주요 수치
    # ══════════════════════════════════════════════════════════
    pdf.new_page()

    pdf.section_title("핵심 요약 (Executive Summary)", "1")
    pdf.body_text(
        "2026년 3월 10일, NVIDIA CEO 젠슨 황(Jensen Huang)은 Fortune 인터뷰에서 "
        "현재 7,000억 달러(약 1,021조 원) 규모의 AI 인프라 투자는 '시작에 불과하다'고 "
        "선언했다. 그는 향후 수조 달러 규모의 추가 인프라 구축이 필요하며, "
        "2030년까지 연간 최대 4조 달러의 AI 데이터센터 인프라 지출이 예상된다고 밝혔다. "
        "이 발언은 GTC 2026(3월 16~19일) 개막을 일주일 앞두고 나온 것으로, "
        "차세대 GPU 플랫폼 '베라 루빈(Vera Rubin)' 공개와 함께 AI 산업의 새로운 "
        "이정표를 제시할 것으로 기대된다."
    )

    pdf.ln(2)
    pdf.section_title("주요 핵심 수치", "2")
    pdf.ln(2)
    pdf.key_stat_box("현재 빅테크 AI 설비투자 합산 (2026년)", "$7,000억", "약 1,021조 원 | 스웨덴+이스라엘+아르헨 GDP 초과")
    pdf.key_stat_box("2030년 연간 AI 인프라 지출 전망", "$4조", "Jensen Huang 추정치")
    pdf.key_stat_box("맥킨지 2030년 누적 데이터센터 투자 전망", "$6.7조", "글로벌 누적 기준")
    pdf.key_stat_box("NVIDIA FY2026 연간 매출", "$2,159억", "전년 대비 65% 성장")
    pdf.key_stat_box("NVIDIA Q4 FY2026 분기 매출", "$681억", "전년 동기 대비 73% 성장")
    pdf.key_stat_box("NVIDIA 데이터센터 부문 연매출", "$1,937억", "FY2026 기준, 68% YoY 성장")

    # ══════════════════════════════════════════════════════════
    # Page 3: 젠슨 황 핵심 발언 상세
    # ══════════════════════════════════════════════════════════
    pdf.new_page()

    pdf.section_title("젠슨 황 핵심 발언 분석", "3")

    pdf.sub_title("AI 인프라 투자: 시작에 불과하다")
    pdf.quote_box(
        "We have only just begun this buildout. We are a few hundred billion dollars into it. "
        "Trillions of dollars of infrastructure still need to be built.",
        "Jensen Huang, Fortune Interview (2026.03.10)"
    )
    pdf.body_text(
        "젠슨 황은 현재까지 투입된 수천억 달러가 전체 AI 인프라 건설의 초기 단계에 "
        "불과하다고 강조했다. 그에 따르면 AI 워크로드에 필요한 컴퓨팅 용량은 "
        "기존 클래식 컴퓨팅 인프라 대비 '1,000배' 이상이며, 이를 충족하기 위해서는 "
        "수조 달러 규모의 지속적인 투자가 불가피하다."
    )

    pdf.sub_title("AI 거품론에 대한 반박")
    pdf.quote_box(
        "AI 거품은 없습니다. 우리는 수십조 달러에 달하는 인류 역사상 최대 규모 "
        "인프라 프로젝트의 시작점에 서 있을 뿐입니다.",
        "Jensen Huang, 한국경제 인터뷰 (2026.02)"
    )
    pdf.body_text(
        "AI 버블 우려에 대해 황은 단호하게 반박했다. 그는 현재의 AI 투자가 "
        "인터넷 버블과 근본적으로 다르며, 실질적인 생산성 향상과 경제적 가치를 "
        "창출하고 있다고 주장했다. 실제로 하버드 경제학자 Jason Furman은 "
        "데이터센터 없이는 2025년 상반기 미국 GDP 성장률이 0.1%에 불과했을 것이라고 "
        "분석했으며, JPMorgan의 Stephanie Aliaga는 AI 관련 자본지출이 GDP 성장에 "
        "1.1%p 기여하여 소비 지출을 초과했다고 평가했다."
    )

    pdf.sub_title("노동 시장에 미치는 영향")
    pdf.body_text(
        "황은 AI 인프라 건설에 전기기사, 배관공, 철강 노동자, 기술자 등 "
        "'엄청난(enormous)' 규모의 노동력이 필요하다고 강조했다. 미국 노동통계국은 "
        "2034년까지 전기기사 수요가 9% 증가하며, 연간 평균 81,000개의 일자리가 "
        "창출될 것으로 전망했다. 다만 브루킹스 연구소는 데이터센터 건설이 "
        "일시적 고용을 생성하며 장기적 전망은 제한적이라고 경고했다."
    )

    # ══════════════════════════════════════════════════════════
    # Page 4: GTC 2026 & 차세대 기술
    # ══════════════════════════════════════════════════════════
    pdf.new_page()

    pdf.section_title("GTC 2026 컨퍼런스 & 차세대 기술 공개", "4")

    pdf.sub_title("GTC 2026 개요")
    pdf.bullet("일시: 2026년 3월 16~19일 (4일간)")
    pdf.bullet("장소: 미국 캘리포니아 산호세, SAP Center 및 10개 다운타운 회장")
    pdf.bullet("규모: 190개국 이상에서 30,000명 이상 참가 예상")
    pdf.bullet("키노트: 3월 16일 오전 11시(PT), 젠슨 황 CEO 기조연설 (라이브 스트리밍)")
    pdf.bullet("참가 기업: Tesla, OpenAI, Meta, Microsoft, Google DeepMind 등")
    pdf.bullet("240개 이상 NVIDIA Inception 스타트업 데모 전시")

    pdf.sub_title("5계층 AI 인프라 프레임워크")
    pdf.body_text(
        "NVIDIA는 GTC 2026에서 GPU 판매를 넘어 전체 AI 생태계를 관통하는 "
        "5계층 인프라 프레임워크를 제시할 예정이다:"
    )
    pdf.bullet("1계층 - 에너지(Energy): AI 데이터센터의 전력 공급 인프라")
    pdf.bullet("2계층 - 칩(Chips): GPU, DPU, 네트워킹 반도체")
    pdf.bullet("3계층 - 인프라(Infrastructure): 데이터센터, 냉각, 네트워크")
    pdf.bullet("4계층 - 모델(Models): 파운데이션 모델, 에이전트 AI")
    pdf.bullet("5계층 - 애플리케이션(Applications): 자율주행, 로보틱스, 디지털 트윈")

    pdf.ln(2)
    pdf.sub_title("차세대 GPU 플랫폼 로드맵")
    pdf.ln(2)

    col_w = [50, 45, 45, 50]
    pdf.table_row(["플랫폼", "출시 시기", "메모리", "주요 특징"], is_header=True, col_widths=col_w)
    pdf.table_row(["Vera Rubin", "2026 H2", "HBM4 x 8", "블랙웰 대비 5배 성능"], col_widths=col_w)
    pdf.table_row(["Rubin Ultra", "2027", "HBM4 x 12", "차세대 울트라 플래그십"], col_widths=col_w)
    pdf.table_row(["Feynman", "2028 (예상)", "HBM5", "광학 인터커넥트(CPO) 통합"], col_widths=col_w)

    pdf.ln(4)
    pdf.sub_title("Vera Rubin 플랫폼 핵심 성능")
    pdf.bullet("블랙웰 대비 AI 모델 학습 시 GPU 사용량 75% 절감")
    pdf.bullet("추론 토큰 비용 90% 절감")
    pdf.bullet("GPU당 HBM4 메모리 8개 탑재, 메모리 대역폭 병목 해소")
    pdf.bullet("현재 양산 착수 상태, 2026년 하반기 상용 출하 시작")

    # ══════════════════════════════════════════════════════════
    # Page 5: HBM4 공급 경쟁 & NVIDIA 재무
    # ══════════════════════════════════════════════════════════
    pdf.new_page()

    pdf.section_title("HBM4 공급망 경쟁 구도", "5")
    pdf.body_text(
        "차세대 GPU 플랫폼의 핵심인 HBM4(High Bandwidth Memory 4세대) 메모리를 둘러싸고 "
        "삼성전자와 SK하이닉스 간의 공급 경쟁이 본격화되고 있다."
    )
    pdf.bullet("SK하이닉스: 1차 공급사로 NVIDIA와 긴밀 협력 중, HBM4 양산 진행")
    pdf.bullet("삼성전자: HBM4 양산 준비 착수, 경쟁력 회복에 총력")
    pdf.bullet("젠슨 황 평가: '삼성의 경쟁력이 시장에 긍정적 긴장감을 제공한다'")
    pdf.bullet("기술 방향: 3D 스태킹 기술 도입 검토, 메모리 대역폭 병목 해소가 핵심 과제")

    pdf.ln(2)
    pdf.section_title("NVIDIA 재무 현황 및 밸류에이션", "6")
    pdf.ln(2)

    col_w2 = [90, 100]
    pdf.table_row(["지표", "수치"], is_header=True, col_widths=col_w2)
    pdf.table_row(["FY2026 연간 매출", "$2,159억 (65% YoY)"], col_widths=col_w2)
    pdf.table_row(["Q4 FY2026 분기 매출", "$681억 (73% YoY)"], col_widths=col_w2)
    pdf.table_row(["데이터센터 부문 FY2026", "$1,937억 (68% YoY)"], col_widths=col_w2)
    pdf.table_row(["Q1 FY2027 가이던스", "$780억 (77% YoY 예상)"], col_widths=col_w2)
    pdf.table_row(["공급 약정 증가", "$503억 -> $952억"], col_widths=col_w2)
    pdf.table_row(["시가총액", "약 $4.43조"], col_widths=col_w2)
    pdf.table_row(["현재 주가", "$182.48"], col_widths=col_w2)
    pdf.table_row(["현재 P/E", "36.1x (10년 평균 61.6x 대비 41% 할인)"], col_widths=col_w2)
    pdf.table_row(["Forward P/E", "21.5x"], col_widths=col_w2)
    pdf.table_row(["Citi 목표가", "$270"], col_widths=col_w2)

    pdf.ln(4)
    pdf.sub_title("빅테크 AI 설비투자 동향")
    pdf.body_text(
        "4대 하이퍼스케일러(Microsoft, Amazon, Google, Meta)의 2026년 설비투자 합산은 "
        "7,000억 달러(약 1,021조 원)에 육박하며, 모건스탠리는 하이퍼스케일러 차입이 "
        "올해 4,000억 달러(약 583조 원)에 이를 것으로 전망했다. "
        "이 규모는 스웨덴, 이스라엘, 아르헨티나의 GDP를 합한 것보다 크며, "
        "디즈니, 나이키, 타깃의 시가총액 합계를 초과하고, "
        "인플레이션 조정 아폴로 프로그램 비용을 압도하는 수준이다."
    )

    # ══════════════════════════════════════════════════════════
    # Page 6: 투자 시사점 & 리스크
    # ══════════════════════════════════════════════════════════
    pdf.new_page()

    pdf.section_title("투자 시사점", "7")

    pdf.sub_title("긍정적 요인 (Bull Case)")
    pdf.bullet(
        "AI 인프라 투자 사이클은 초기 단계: 현재 수천억 달러 투자는 향후 수조 달러 "
        "시장의 시작점에 불과하며, NVIDIA는 GPU + 풀스택 전략으로 최대 수혜 예상"
    )
    pdf.bullet(
        "Vera Rubin 효율성 혁신: 학습 GPU 75% 절감, 추론 비용 90% 절감은 "
        "AI 도입 기업의 ROI를 극적으로 개선하여 수요 가속화 전망"
    )
    pdf.bullet(
        "밸류에이션 매력: 현재 P/E 36.1x는 10년 평균(61.6x) 대비 41% 할인 상태, "
        "Forward P/E 21.5x로 성장률 대비 합리적 수준"
    )
    pdf.bullet(
        "GDP 기여도 입증: AI 자본지출이 미국 GDP 성장의 1.1%p를 차지, "
        "실질적 경제 가치 창출이 데이터로 확인됨"
    )

    pdf.sub_title("리스크 요인 (Bear Case)")
    pdf.bullet(
        "과잉투자 우려: 7,000억 달러 규모의 설비투자가 실제 AI 수요를 초과할 가능성, "
        "하이퍼스케일러 차입 4,000억 달러는 금리 환경에 따라 부담 가중"
    )
    pdf.bullet(
        "빅테크 구조조정 병행: Amazon 16,000명 감원 등 AI 투자 확대와 동시에 "
        "인력 구조조정 진행, 수익성 압박 신호 가능"
    )
    pdf.bullet(
        "지정학적 리스크: 미중 반도체 규제, 대만 해협 긴장 등이 NVIDIA 공급망에 "
        "영향을 줄 수 있으며, 수출 규제 강화 가능성 상존"
    )
    pdf.bullet(
        "데이터센터 고용의 한시성: 브루킹스 연구소 경고처럼 건설 단계 고용은 "
        "일시적이며, 장기 일자리 창출 효과는 제한적"
    )

    pdf.ln(2)
    pdf.section_title("한국 투자자 관점", "8")
    pdf.bullet(
        "반도체 수혜: SK하이닉스(HBM4 1차 공급사)와 삼성전자(HBM4 양산 준비)가 "
        "NVIDIA 차세대 플랫폼의 핵심 공급사로, 직접적 매출 성장 기대"
    )
    pdf.bullet(
        "환율 리스크: 달러/원 환율 변동이 해외 반도체주 투자 수익률에 영향, "
        "원화 약세 시 해외 투자 수익 극대화 가능하나 환 헤지 전략 고려 필요"
    )
    pdf.bullet(
        "국내 AI 인프라 투자 확대: 정부의 2027 AI Top 3 전략과 맞물려 "
        "데이터센터 건설, 전력 인프라 확대 등 국내 관련주에도 투자 기회"
    )
    pdf.bullet(
        "GTC 2026(3월 16일) 키노트 이후 반도체 섹터 변동성 확대 가능, "
        "이벤트 전후 포지션 관리에 유의"
    )

    # ══════════════════════════════════════════════════════════
    # Page 7: 참고 자료
    # ══════════════════════════════════════════════════════════
    pdf.new_page()

    pdf.section_title("참고 자료 (Sources)", "9")
    pdf.ln(2)

    sources = [
        ("Fortune - Jensen Huang: AI needs trillions more in infrastructure",
         "https://fortune.com/2026/03/10/jensen-huang-ai-infrastructure-buildout-700-billion/"),
        ("Motley Fool - Jensen Huang Incredible News for Nvidia Investors",
         "https://www.fool.com/investing/2026/03/06/jensen-huang-incredible-news-nvidia-stock-investor/"),
        ("NVIDIA Newsroom - GTC 2026 Announcement",
         "https://nvidianews.nvidia.com/news/nvidia-ceo-jensen-huang-and-global-technology-leaders-to-showcase-age-of-ai-at-gtc-2026"),
        ("ainvest - Jensen Huang $700B AI Buildout Is Just the Beginning",
         "https://www.ainvest.com/news/jensen-huang-700-billion-ai-buildout-beginning/"),
        ("Blockchain News - NVIDIA GTC 2026 AI Stack Reveal",
         "https://blockchain.news/news/nvidia-gtc-2026-jensen-huang-ai-stack-march"),
        ("TipRanks - NVIDIA GTC 2026 Preview",
         "https://www.tipranks.com/news/nvidia-nvda-gtc-2026-is-coming-heres-what-to-expect/"),
        ("한국경제 - 젠슨 황, AI 투자 시작 단계... 버블은 없다",
         "https://www.hankyung.com/article/2026021897121"),
        ("글로벌이코노믹 - 젠슨 황, GTC 2026서 세상 못 본 칩 여러 개 꺼낸다",
         "https://www.g-enews.com/article/Global-Biz/2026/02/202602200717314727fbbec65dfb_1"),
        ("경향게임스 - GTC 2026, 엔비디아 AI 인프라의 미래 조명",
         "https://www.khgames.co.kr/news/articleView.html?idxno=301993"),
        ("NVIDIA Blog Korea - GTC 2026에서 AI 시대 선보이다",
         "https://blogs.nvidia.co.kr/blog/nvidia-ceo-jensen-huang-and-global-technology-leaders-to-showcase-age-of-ai-at-gtc-2026/"),
    ]
    for name, url in sources:
        pdf.source_item(name, url)

    pdf.ln(6)

    # Disclaimer
    pdf.set_font("Malgun", "", 8)
    pdf.set_text_color(*pdf.MUTED)
    pdf.set_x(15)
    pdf.multi_cell(180, 5,
        "Disclaimer: 본 보고서는 공개된 뉴스 및 기업 발표 자료를 기반으로 정리한 참고 자료이며, "
        "투자 권유를 목적으로 하지 않습니다. 투자 판단은 본인의 책임하에 이루어져야 합니다."
    )

    # Save
    output_path = "C:/Users/LENOVO1430/ClaudeCode/Invest/reports/Jensen_Huang_AI_Infra_Report_20260311.pdf"
    pdf.output(output_path)
    print(f"PDF 생성 완료: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_report()
