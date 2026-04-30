"""Generate 5 synthetic Korean equipment manuals as PDFs.

Why a generator instead of static PDFs:
- Deterministic content => evaluation set (AI-05) can pin exact pages.
- Re-runnable on any machine without committing binary blobs.
- Each manual lands at >= 10 pages with a labelled error-code section.

Run:
    uv run python scripts/generate_manuals.py
Outputs:
    data/manuals/<equipment_id>_manual.pdf      x5
    data/manuals/README.md                       (manifest)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "manuals"


@dataclass(frozen=True)
class ErrorCode:
    code: str
    title: str
    cause: str
    action: str
    severity: str  # low | medium | high | critical


@dataclass(frozen=True)
class Equipment:
    equipment_id: str
    equipment_name: str
    filename: str
    overview: str
    specs: list[tuple[str, str]]
    safety_notes: list[str]
    operation_steps: list[str]
    maintenance_steps: list[str]
    error_codes: list[ErrorCode]


# 5 equipments x 4 codes = 20 codes total.
EQUIPMENTS: list[Equipment] = [
    Equipment(
        equipment_id="eq_pv300",
        equipment_name="공압 밸브 PV-300",
        filename="pv300_manual.pdf",
        overview=(
            "PV-300은 식음료 공정 라인에 사용되는 고속 공압 액추에이터 밸브입니다. "
            "표준 작동 압력은 0.5~0.7 MPa이며, 응답 시간은 50ms 이하입니다."
        ),
        specs=[
            ("작동 압력", "0.5 ~ 0.7 MPa"),
            ("응답 시간", "≤ 50 ms"),
            ("동작 온도", "-10°C ~ 80°C"),
            ("방진/방수", "IP65"),
        ],
        safety_notes=[
            "정비 전 라인 압력을 0으로 배출한다.",
            "고압 라인 분리 시 보호장갑과 보안경을 착용한다.",
            "전기 신호선 분리 후 기계적 잠금을 적용한다.",
        ],
        operation_steps=[
            "전원 인가 후 자체 진단 LED가 녹색이 될 때까지 5초 대기한다.",
            "PLC에서 OPEN 신호를 1초 이상 인가한다.",
            "압력 게이지가 설정값에 도달하는지 확인한다.",
            "CLOSE 신호 인가 후 누설이 없는지 1분간 관찰한다.",
        ],
        maintenance_steps=[
            "주 1회: 외관 검사 및 누설 점검.",
            "월 1회: 액추에이터 응답 시간 측정.",
            "분기 1회: 시일 및 다이어프램 교체 권장.",
            "연 1회: 전체 분해 정비 및 교정.",
        ],
        error_codes=[
            ErrorCode(
                "E-201",
                "공급 압력 부족",
                "공기 공급 압력이 0.5 MPa 미만입니다.",
                "공기 압축기 출력과 공급 라인 누설을 점검하고, 필요 시 압축기를 재가동합니다.",
                "high",
            ),
            ErrorCode(
                "E-202",
                "위치 센서 신호 손실",
                "OPEN/CLOSE 위치 센서가 응답하지 않습니다.",
                "센서 커넥터 분리 후 재연결, 단선 여부를 확인하고 손상 시 센서를 교체합니다.",
                "medium",
            ),
            ErrorCode(
                "E-203",
                "내부 누설 감지",
                "밸브 시트 또는 시일이 마모되어 내부 누설이 발생했습니다.",
                "라인을 차단하고 시일 키트를 교체합니다. 마모가 심한 경우 시트도 교체합니다.",
                "high",
            ),
            ErrorCode(
                "E-204",
                "액추에이터 응답 시간 초과",
                "OPEN/CLOSE 명령에 50ms 이상 응답 지연이 발생했습니다.",
                "공급 압력과 액추에이터 시일 상태를 점검하고, 노후된 다이어프램을 교체합니다.",
                "high",
            ),
        ],
    ),
    Equipment(
        equipment_id="eq_cv550",
        equipment_name="컨베이어 모터 CV-550",
        filename="cv550_manual.pdf",
        overview=(
            "CV-550은 자동화 라인용 가변속 컨베이어 모터입니다. "
            "정격 출력 5.5 kW, 최대 속도 1750 RPM의 인버터 구동 방식을 채택했습니다."
        ),
        specs=[
            ("정격 출력", "5.5 kW"),
            ("정격 전압", "AC 380V 3상"),
            ("최대 RPM", "1750"),
            ("절연 등급", "Class F"),
        ],
        safety_notes=[
            "정비 전 인버터 차단기를 OFF하고 5분간 잔류 전압을 방전한다.",
            "체인/벨트 작업 시 회전부에서 손을 멀리 한다.",
            "고온 가동 직후에는 케이싱 표면을 직접 만지지 않는다.",
        ],
        operation_steps=[
            "인버터 파라미터(P0, P1)가 라인 사양과 일치하는지 확인한다.",
            "수동 모드로 30 RPM 시운전 후 진동을 점검한다.",
            "자동 모드 전환 후 부하율 70% 이내인지 모니터링한다.",
            "비상정지 회로의 동작을 매일 1회 점검한다.",
        ],
        maintenance_steps=[
            "주 1회: 베어링 소음 청취 및 진동값 기록.",
            "월 1회: 그리스 보충(SKF LGEP2 권장).",
            "분기 1회: 절연 저항 측정(메가옴 테스터, 1kV).",
            "연 1회: 인버터 콘덴서 점검 및 베어링 교체 검토.",
        ],
        error_codes=[
            ErrorCode(
                "E-301",
                "과전류",
                "정격 전류의 150%를 초과한 부하가 감지되었습니다.",
                "벨트 장력과 컨베이어 적재량을 줄이고, 인버터 부하 파라미터를 재설정합니다.",
                "critical",
            ),
            ErrorCode(
                "E-302",
                "베어링 진동 초과",
                "진동값이 4.0 mm/s를 초과합니다.",
                "베어링 윤활 상태를 점검하고, 마모가 확인되면 즉시 베어링을 교체합니다.",
                "high",
            ),
            ErrorCode(
                "E-303",
                "권선 온도 상승",
                "스테이터 온도가 130°C를 초과합니다.",
                "냉각팬 동작과 흡입구 막힘을 확인하고, 부하율을 재계산합니다.",
                "high",
            ),
            ErrorCode(
                "E-304",
                "인코더 신호 이상",
                "엔코더 펄스 카운트가 불연속적입니다.",
                "엔코더 케이블 차폐 접지를 확인하고 손상 시 엔코더를 교체합니다.",
                "medium",
            ),
        ],
    ),
    Equipment(
        equipment_id="eq_hp120",
        equipment_name="유압 프레스 HP-120",
        filename="hp120_manual.pdf",
        overview=(
            "HP-120은 120톤급 유압 프레스로, 프레스 가공 및 펀칭 공정에 사용됩니다. "
            "최대 작동 압력은 21 MPa이며 PLC 기반 시퀀스 제어를 지원합니다."
        ),
        specs=[
            ("정격 가압력", "120 ton"),
            ("최대 유압", "21 MPa"),
            ("스트로크", "300 mm"),
            ("작동유", "ISO VG 46"),
        ],
        safety_notes=[
            "양손 누름 회로의 동시성(0.5초 이내)을 매일 점검한다.",
            "라이트 커튼이 차단되었을 때 프레스가 즉시 정지하는지 확인한다.",
            "유압 호스 교체 시 라인 압력을 완전히 배출한다.",
        ],
        operation_steps=[
            "유압 펌프 기동 후 5분간 무부하 워밍업한다.",
            "금형 위치를 정렬하고 토크 렌치로 60 N·m 체결한다.",
            "시운전 시 1톤 부하부터 단계적으로 증가시킨다.",
            "사이클 종료 후 유온 60°C 이하인지 확인한다.",
        ],
        maintenance_steps=[
            "주 1회: 유면 게이지와 누유 점검.",
            "월 1회: 압력 릴리프 밸브 동작 시험.",
            "분기 1회: 작동유 오염도 측정(NAS 9 이내).",
            "연 1회: 작동유 전체 교환 및 필터 교체.",
        ],
        error_codes=[
            ErrorCode(
                "E-401",
                "유압 압력 저하",
                "주 라인 압력이 18 MPa 미만으로 떨어졌습니다.",
                "유압 펌프 출력, 릴리프 밸브 셋팅, 라인 누유를 순서대로 점검합니다.",
                "critical",
            ),
            ErrorCode(
                "E-402",
                "작동유 온도 과열",
                "작동유 온도가 70°C를 초과합니다.",
                "쿨러 송풍팬과 작동유 레벨을 확인하고, 오염 시 작동유를 교환합니다.",
                "high",
            ),
            ErrorCode(
                "E-403",
                "라이트 커튼 페일",
                "안전 라이트 커튼 자가진단이 실패했습니다.",
                "송수광부 정렬과 케이블 단선을 점검하고, 안전 컨트롤러를 리셋합니다.",
                "critical",
            ),
            ErrorCode(
                "E-404",
                "양손 누름 동시성 오류",
                "두 누름 버튼의 입력 시간차가 0.5초를 초과했습니다.",
                "버튼 접점 마모와 PLC 입력 모듈 응답 시간을 점검합니다.",
                "high",
            ),
        ],
    ),
    Equipment(
        equipment_id="eq_rb900",
        equipment_name="협동 로봇 RB-900",
        filename="rb900_manual.pdf",
        overview=(
            "RB-900은 6축 협동 로봇으로 가반하중 9 kg, 작업 반경 1300 mm입니다. "
            "조작자와의 직접 협업이 가능하며 충돌 감지 기능을 내장하고 있습니다."
        ),
        specs=[
            ("자유도", "6축"),
            ("가반 하중", "9 kg"),
            ("작업 반경", "1300 mm"),
            ("반복 정밀도", "±0.05 mm"),
        ],
        safety_notes=[
            "협동 모드와 일반 모드의 속도 한계가 다름을 인지한다.",
            "충돌 감지 후에는 반드시 원인을 확인 후 해제한다.",
            "외부 안전 PLC와의 듀얼 채널 회로를 분기마다 점검한다.",
        ],
        operation_steps=[
            "전원 인가 후 캘리브레이션 자세(Home)를 확인한다.",
            "툴 무게와 무게 중심을 컨트롤러에 등록한다.",
            "프로그램 실행 전 단계 모드(Step)로 경로를 검증한다.",
            "운영 중 안전 펜스/광커튼 상태를 모니터링한다.",
        ],
        maintenance_steps=[
            "주 1회: 케이블 외피 손상 점검.",
            "월 1회: 각 관절 백래시 측정.",
            "분기 1회: 그리스 충진 및 토크 재조정.",
            "연 1회: 마스터 캘리브레이션 재수행.",
        ],
        error_codes=[
            ErrorCode(
                "E-501",
                "충돌 감지 트리거",
                "관절 토크가 한계값을 초과해 충돌로 판정되었습니다.",
                "주변 장애물을 제거하고 경로를 재검증한 뒤 안전 리셋을 수행합니다.",
                "high",
            ),
            ErrorCode(
                "E-502",
                "관절 엔코더 오차",
                "엔코더 카운트가 모터 회전수와 일치하지 않습니다.",
                "엔코더 커플링 슬립을 확인하고 캘리브레이션을 재수행합니다.",
                "high",
            ),
            ErrorCode(
                "E-503",
                "안전 입력 단선",
                "비상정지 또는 안전 펜스 입력이 단선 상태입니다.",
                "이중화 입력 라인의 연속성을 멀티미터로 점검하고, 손상 시 케이블을 교체합니다.",
                "critical",
            ),
            ErrorCode(
                "E-504",
                "툴 통신 장애",
                "툴 플랜지의 디지털 I/O 통신이 실패했습니다.",
                "툴 커넥터 핀 오염을 청소하고, 통신 속도를 250 kbps로 재설정합니다.",
                "medium",
            ),
        ],
    ),
    Equipment(
        equipment_id="eq_cn450",
        equipment_name="CNC 머시닝센터 CN-450",
        filename="cn450_manual.pdf",
        overview=(
            "CN-450은 3축 수직형 머시닝센터로 주축 회전수 12000 RPM, "
            "이송 속도 24 m/min을 지원합니다. 자동 공구 교환장치(ATC)를 갖추고 있습니다."
        ),
        specs=[
            ("주축 최대 RPM", "12000"),
            ("이송 속도", "24 m/min"),
            ("X/Y/Z 스트로크", "800/500/450 mm"),
            ("ATC 공구 수", "20"),
        ],
        safety_notes=[
            "도어 인터록이 동작 중 해제되면 즉시 정지하는지 확인한다.",
            "절삭유 분사 노즐 정비 시 항상 펌프를 OFF한다.",
            "주축 가동 중에는 공구 매거진에 손을 넣지 않는다.",
        ],
        operation_steps=[
            "전원 인가 후 X/Y/Z 원점 복귀를 수행한다.",
            "공구 길이/직경 보정값을 검증한다.",
            "1차 시제품을 단동 모드(Single Block)로 가공한다.",
            "치수 검사 후 자동 모드로 전환한다.",
        ],
        maintenance_steps=[
            "주 1회: 가이드 슬라이드 윤활 점검.",
            "월 1회: 절삭유 농도/오염도 측정.",
            "분기 1회: 볼스크류 백래시 측정.",
            "연 1회: 주축 베어링 점검 및 정밀도 재교정.",
        ],
        error_codes=[
            ErrorCode(
                "E-601",
                "주축 과부하",
                "주축 모터의 부하율이 110%를 초과했습니다.",
                "절삭 조건(이송, 절입량)을 줄이고 공구 마모 상태를 확인합니다.",
                "high",
            ),
            ErrorCode(
                "E-602",
                "ATC 공구 미장착",
                "ATC가 공구를 매거진에서 인식하지 못했습니다.",
                "공구 홀더 오염을 청소하고, 매거진 인덱싱 위치를 재학습합니다.",
                "medium",
            ),
            ErrorCode(
                "E-603",
                "축 위치 편차",
                "지령 위치와 실제 위치 편차가 0.02 mm를 초과합니다.",
                "서보 게인과 볼스크류 백래시를 확인하고, 필요 시 볼스크류를 재예압합니다.",
                "high",
            ),
            ErrorCode(
                "E-604",
                "절삭유 압력 저하",
                "절삭유 라인 압력이 0.3 MPa 미만입니다.",
                "절삭유 탱크 레벨과 펌프 흡입구 막힘을 점검하고, 필터를 교체합니다.",
                "low",
            ),
        ],
    ),
]


# ---------- PDF rendering ----------

PAGE_W, PAGE_H = 595, 842  # A4 in points
MARGIN_X = 50
MARGIN_Y_TOP = 60
MARGIN_Y_BOTTOM = 60
LINE_HEIGHT = 16
TITLE_SIZE = 18
H1_SIZE = 14
BODY_SIZE = 11

# PyMuPDF cannot render Hangul with its built-in PDF base14 fonts.
# We bundle the system Korean font that ships with Windows.
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"
FONT_NAME = "malgun"


class PdfBuilder:
    def __init__(self) -> None:
        self.doc = fitz.open()
        self._new_page()

    def _new_page(self) -> None:
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.page.insert_font(fontname=FONT_NAME, fontfile=FONT_PATH)
        self.y = MARGIN_Y_TOP

    def _ensure_room(self, needed: float) -> None:
        if self.y + needed > PAGE_H - MARGIN_Y_BOTTOM:
            self._new_page()

    def title(self, text: str) -> None:
        self._ensure_room(TITLE_SIZE + 12)
        self.page.insert_text(
            (MARGIN_X, self.y + TITLE_SIZE),
            text,
            fontname=FONT_NAME,
            fontsize=TITLE_SIZE,
        )
        self.y += TITLE_SIZE + 14

    def heading(self, text: str) -> None:
        self._ensure_room(H1_SIZE + 12)
        self.y += 6
        self.page.insert_text(
            (MARGIN_X, self.y + H1_SIZE),
            text,
            fontname=FONT_NAME,
            fontsize=H1_SIZE,
        )
        self.y += H1_SIZE + 8

    def line(self, text: str) -> None:
        self._ensure_room(LINE_HEIGHT)
        self.page.insert_text(
            (MARGIN_X, self.y + BODY_SIZE),
            text,
            fontname=FONT_NAME,
            fontsize=BODY_SIZE,
        )
        self.y += LINE_HEIGHT

    def paragraph(self, text: str, indent: float = 0.0) -> None:
        # naive wrap by character width estimate (Korean: ~1 char per body_size units)
        max_chars = int((PAGE_W - 2 * MARGIN_X - indent) / (BODY_SIZE * 0.6))
        words = text.split()
        line: list[str] = []
        cur_len = 0
        for w in words:
            wl = len(w) + 1
            if cur_len + wl > max_chars and line:
                self._draw_indented(" ".join(line), indent)
                line, cur_len = [w], wl
            else:
                line.append(w)
                cur_len += wl
        if line:
            self._draw_indented(" ".join(line), indent)
        self.y += 4

    def _draw_indented(self, text: str, indent: float) -> None:
        self._ensure_room(LINE_HEIGHT)
        self.page.insert_text(
            (MARGIN_X + indent, self.y + BODY_SIZE),
            text,
            fontname=FONT_NAME,
            fontsize=BODY_SIZE,
        )
        self.y += LINE_HEIGHT

    def page_break(self) -> None:
        self._new_page()

    def current_page_number(self) -> int:
        return self.page.number + 1  # 1-indexed for humans

    def save(self, path: Path) -> int:
        self.doc.save(str(path))
        n = self.doc.page_count
        self.doc.close()
        return n


def build_manual(eq: Equipment) -> tuple[Path, int, dict[str, list[int]]]:
    """Render one manual PDF; return (path, page_count, error_code_pages)."""
    b = PdfBuilder()
    error_pages: dict[str, list[int]] = {}

    # ----- p1: title -----
    b.title(f"{eq.equipment_name} 운영 매뉴얼")
    b.line(f"장비 ID: {eq.equipment_id}")
    b.line("문서 버전: v1.0  |  발행일: 2026-04-30")
    b.line("발행: FactoryGuard Documentation Team")
    b.paragraph("")
    b.heading("개요")
    b.paragraph(eq.overview)

    # ----- p2: specs -----
    b.page_break()
    b.heading("1. 사양")
    for k, v in eq.specs:
        b.line(f"  - {k}: {v}")
    b.paragraph("")
    b.paragraph(
        "본 사양은 표준 출하 기준이며, 옵션 사양에 따라 일부 값이 달라질 수 있습니다. "
        "현장 설치 후에는 시운전을 통해 사양 적합성을 확인하십시오."
    )

    # ----- p3: safety -----
    b.page_break()
    b.heading("2. 안전 수칙")
    for i, note in enumerate(eq.safety_notes, 1):
        b.paragraph(f"{i}) {note}")
    b.paragraph(
        "안전 수칙을 위반할 경우 인명 사고 또는 장비 손상이 발생할 수 있습니다. "
        "정비 책임자는 본 매뉴얼의 내용을 모든 작업자에게 사전 교육해야 합니다."
    )

    # ----- p4: operation -----
    b.page_break()
    b.heading("3. 운영 절차")
    for i, step in enumerate(eq.operation_steps, 1):
        b.paragraph(f"{i}. {step}")
    b.paragraph(
        "초기 운전 시 PLC 인터록과 비상정지 회로의 동작을 반드시 확인한 후 자동 모드로 전환하십시오."
    )

    # ----- p5: maintenance -----
    b.page_break()
    b.heading("4. 정기 점검")
    for step in eq.maintenance_steps:
        b.paragraph(f"  - {step}")
    b.paragraph(
        "정비 이력은 CMMS(설비관리 시스템)에 빠짐없이 기록하여 다음 정비 일정의 기준 자료로 활용합니다."
    )

    # ----- p6: troubleshooting overview -----
    b.page_break()
    b.heading("5. 오류 코드 (Error Codes)")
    b.paragraph(
        "본 장에서는 컨트롤러가 표시하는 오류 코드와 권장 조치를 설명합니다. "
        "코드는 알람 패널 또는 운영 SCADA에 표시되며, 각 코드는 즉시 조치 지침을 포함합니다."
    )
    b.paragraph("아래 표는 본 장비에서 발생 가능한 주요 오류 코드의 요약입니다.")
    for ec in eq.error_codes:
        b.line(f"  - {ec.code} : {ec.title}  (심각도: {ec.severity})")

    # ----- p7+: per-error detail (each on its own page so eval set can pin pages) -----
    for ec in eq.error_codes:
        b.page_break()
        b.heading(f"5.{ec.code[2:]} 오류 코드 {ec.code} — {ec.title}")
        page1 = b.current_page_number()
        b.paragraph(f"심각도: {ec.severity}")
        b.heading("증상 및 원인")
        b.paragraph(ec.cause)
        b.heading("권장 조치")
        b.paragraph(ec.action)
        b.heading("관련 점검 항목")
        b.paragraph(
            "조치 후에는 운영 절차(3장)와 정기 점검 항목(4장)을 다시 확인하여 "
            "재발 가능성을 평가하고, 필요 시 정비 주기를 단축합니다."
        )
        # second page of detail to give eval set 2 valid pages
        b.page_break()
        page2 = b.current_page_number()
        b.heading(f"오류 코드 {ec.code} — 부록")
        b.paragraph(
            f"{ec.code} 발생 시 다음 추가 정보를 함께 기록하면 근본 원인 분석에 도움이 됩니다."
        )
        b.paragraph("  - 발생 시각, 운전 모드, 직전 작업 내역")
        b.paragraph("  - 환경 조건(온도, 습도, 외부 진동원)")
        b.paragraph("  - 직전 정비 이력 및 교체 부품 번호")
        error_pages[ec.code] = [page1, page2]

    # ----- final appendix -----
    b.page_break()
    b.heading("6. 부록 — 연락처 및 폐기 안내")
    b.paragraph("기술 지원: support@factoryguard.example  /  +82-2-000-0000")
    b.paragraph(
        "장비 폐기 시 작동유 및 윤활유는 산업 폐기물 처리 규정에 따라 위탁 처리하고, "
        "전자 부품은 RoHS 기준에 맞춰 재활용합니다."
    )

    out = OUT_DIR / eq.filename
    page_count = b.save(out)
    return out, page_count, error_pages


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    error_page_index: dict[str, dict[str, list[int]]] = {}

    for eq in EQUIPMENTS:
        path, pages, error_pages = build_manual(eq)
        manifest_rows.append((eq, path, pages))
        error_page_index[eq.equipment_id] = error_pages
        print(f"  wrote {path.name}  pages={pages}")

    # ----- README manifest -----
    readme = OUT_DIR / "README.md"
    lines = [
        "# Equipment Manuals (synthetic)\n",
        "",
        "These 5 PDFs are generated programmatically by `scripts/generate_manuals.py`.",
        "Content is synthetic (no copyrighted material) and pinned so the AI-05",
        "evaluation set can reference exact page numbers.",
        "",
        "| Equipment | Equipment ID | Manual file | Pages | Source / License |",
        "|---|---|---|---|---|",
    ]
    for eq, path, pages in manifest_rows:
        lines.append(
            f"| {eq.equipment_name} | `{eq.equipment_id}` | `{path.name}` | {pages} | "
            "Synthetic (FactoryGuard internal, MIT for project use) |"
        )
    lines += [
        "",
        "## Regenerate",
        "",
        "```bash",
        "uv run python scripts/generate_manuals.py",
        "```",
        "",
        "Regeneration is deterministic — same inputs produce the same PDFs.",
        "",
    ]
    readme.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {readme.relative_to(ROOT)}")

    # ----- side-channel: page index for AI-04/AI-05 -----
    idx_path = OUT_DIR / "_page_index.json"
    idx_path.write_text(
        json.dumps(error_page_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  wrote {idx_path.relative_to(ROOT)}  (used by AI-04/AI-05)")


if __name__ == "__main__":
    main()
