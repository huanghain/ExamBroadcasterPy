"""全局 QSS 样式表 — 紧凑设计系统 v3"""
GLOBAL_STYLESHEET = """
/* ===== 设计令牌 ===== */
/* 主色: 靛蓝 #4F6EF7 */
/* 背景: 冷灰 #F4F6F9 */
/* 圆角: 5px(控件) / 8px(卡片) */

/* ===== 全局 ===== */
QMainWindow { background-color: #F4F6F9; }
#centralWidget { background-color: #F4F6F9; }
QWidget {
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 11px;
    color: #1E293B;
}

/* ===== 标题栏 ===== */
#titleBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
QLabel#titleBarIcon {
    font-size: 14px; font-weight: bold; color: #4F6EF7;
    min-height: 24px; padding: 0 4px;
}
QLabel#titleBarTitle {
    font-size: 13px; font-weight: 600; color: #1E293B;
    min-height: 24px; padding: 0 6px;
}
QLabel#titleBarOfflineTag {
    font-size: 10px; font-weight: bold; color: #991B1B;
    background: #FEE2E2; border: 1px solid #FECACA;
    border-radius: 10px; padding: 1px 8px; min-height: 18px;
}
QPushButton#titleBarMinBtn {
    font-size: 13px; border: none; background: transparent;
    color: #64748B; min-width: 30px; min-height: 24px; padding: 0;
}
QPushButton#titleBarMinBtn:hover {
    background: #F1F5F9; color: #1E293B;
}
QPushButton#titleBarQuitBtn {
    font-size: 11px; border: none; background: transparent;
    color: #DC2626; min-width: 40px; min-height: 24px; padding: 0 6px;
    font-weight: 600;
}
QPushButton#titleBarQuitBtn:hover {
    background: #FEE2E2; color: #B91C1C;
}
QPushButton#titleBarCloseBtn {
    font-size: 13px; border: none; background: transparent;
    color: #64748B; min-width: 30px; min-height: 24px; padding: 0;
}
QPushButton#titleBarCloseBtn:hover {
    background: #EF4444; color: #FFFFFF;
}
QPushButton#titleBarFullscreenBtn {
    font-size: 11px; border: 1px solid #C7D2FE; background: #EEF2FF;
    color: #4F6EF7; min-width: 64px; min-height: 20px; padding: 0 8px;
    border-radius: 4px; margin-right: 6px; font-weight: 600;
}
QPushButton#titleBarFullscreenBtn:hover {
    background: #E0E7FF; border-color: #A5B4FC;
}
QLabel#statusLabel {
    font-size: 11px; color: #64748B;
    min-height: 20px; padding: 0 4px;
}
/* 全屏模式：无声提示层（键盘屏蔽/进入退出的浮动提示，不发声） */
#fullscreenTip {
    background-color: rgba(30, 41, 59, 0.92);
    color: #FFFFFF; font-size: 13px; font-weight: 600;
    border-radius: 8px; padding: 12px 20px;
}
/* 全屏模式：退出确认对话框（自定义 QDialog，避免系统提示音） */
QDialog#fullscreenConfirmDlg {
    background-color: #FFFFFF; border: 1px solid #E2E8F0;
    border-radius: 8px;
}
QLabel#fullscreenConfirmMsg {
    font-size: 13px; color: #1E293B; font-weight: 600;
}
QLabel#fullscreenConfirmHint {
    font-size: 11px; color: #64748B;
}
/* 无声自绘 Toast（不产生任何系统提示音） */
#toast {
    background-color: rgba(24, 32, 48, 0.96);
    border-radius: 8px;
}
QLabel#toastText {
    color: #FFFFFF; font-size: 12px;
}
QLabel#toastIcon {
    font-size: 13px; font-weight: bold;
}
QLabel#toastIcon[kind="info"] { color: #93C5FD; }
QLabel#toastIcon[kind="success"] { color: #4ADE80; }
QLabel#toastIcon[kind="warning"] { color: #FBBF24; }
QLabel#toastIcon[kind="error"] { color: #F87171; }
QPushButton#primaryBtn {
    background: #4F6EF7; color: #FFFFFF; border: none; border-radius: 4px;
    padding: 5px 12px; font-size: 12px; font-weight: 600;
}
QPushButton#primaryBtn:hover { background: #4338CA; }
QPushButton#cancelBtn {
    background: #F1F5F9; color: #334155; border: 1px solid #E2E8F0;
    border-radius: 4px; padding: 5px 12px; font-size: 12px;
}
QPushButton#cancelBtn:hover { background: #E2E8F0; }

/* ===== 导航 ===== */
#navFrame {
    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
}
#navList {
    background-color: transparent;
    border: none; outline: none;
    padding: 4px 8px;
}
#navList::item {
    padding: 7px 12px;
    border-radius: 6px;
    margin: 2px 3px;
    font-size: 12px;
    color: #475569;
}
#navList::item:selected {
    background-color: transparent;
    color: #4F6EF7;
    font-weight: 600;
}
#navList::item:hover:!selected {
    background-color: #F1F5F9;
}
/* 侧边栏选中高亮滑块（背景层，由几何动画驱动平滑滑动） */
#navHighlight {
    background-color: #EEF2FF;
    border-radius: 6px;
}

/* ===== 按钮 ===== */
QPushButton {
    padding: 4px 12px;
    border-radius: 5px;
    font-size: 11px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
    color: #334155;
    min-height: 26px;
}
QPushButton:hover {
    border-color: #4F6EF7;
    color: #4F6EF7;
    background-color: #F8FAFF;
}
QPushButton:pressed {
    background-color: #EEF2FF;
}
QPushButton:disabled {
    color: #94A3B8;
    border-color: #E2E8F0;
    background-color: #F8FAFC;
}

/* 主操作按钮 */
QPushButton#accentBtn {
    background-color: #4F6EF7;
    color: #FFFFFF;
    border: none;
    font-weight: 600;
    min-height: 30px;
    padding: 5px 18px;
}
QPushButton#accentBtn:hover { background-color: #3B5DE7; }
QPushButton#accentBtn:pressed { background-color: #2D4ED6; }
QPushButton#accentBtn:disabled {
    background-color: #A5B4FC;
    color: #EEF2FF;
}

/* 危险按钮 */
QPushButton#dangerBtn {
    color: #EF4444;
    border-color: #FECACA;
    min-height: 26px;
}
QPushButton#dangerBtn:hover {
    background-color: #FFF5F5;
    border-color: #EF4444;
}

/* 标签按钮 */
QPushButton#tagBtn {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    border: 1px solid #E2E8F0;
    background-color: #F8FAFC;
    color: #64748B;
    min-height: 22px;
}
QPushButton#tagBtn:hover {
    border-color: #4F6EF7;
    color: #4F6EF7;
    background-color: #EEF2FF;
}
QPushButton#tagBtn[active="true"] {
    background-color: #4F6EF7;
    color: #FFFFFF;
    border-color: #4F6EF7;
}

/* 表格操作按钮 */
QPushButton#tableActionBtn {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    border: 1px solid #E2E8F0;
    background-color: #F8FAFC;
    color: #64748B;
    min-height: 22px;
}
QPushButton#tableActionBtn:hover {
    border-color: #4F6EF7;
    color: #4F6EF7;
    background-color: #EEF2FF;
}

/* 表格删除按钮 */
QPushButton#tableDeleteBtn {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    border: 1px solid #FECACA;
    background-color: #FFFFFF;
    color: #EF4444;
    min-height: 22px;
}
QPushButton#tableDeleteBtn:hover {
    background-color: #FFF5F5;
    border-color: #EF4444;
}

/* ===== 输入框 ===== */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    padding: 4px 8px;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    background-color: #FFFFFF;
    font-size: 11px;
    min-height: 20px;
    selection-background-color: #4F6EF7;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #4F6EF7;
    border-width: 1.5px;
    padding: 4.5px 9.5px;
    background-color: #FAFBFF;
}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
}

/* ===== 日期/时间选择器 ===== */
QDateEdit, QTimeEdit, QDateTimeEdit {
    padding: 4px 8px;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    background-color: #FFFFFF;
    font-size: 11px;
    min-height: 20px;
}
QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {
    border-color: #4F6EF7;
    border-width: 1.5px;
    padding: 4.5px 9.5px;
}
QDateEdit::drop-down, QTimeEdit::drop-down, QDateTimeEdit::drop-down {
    border: none; width: 20px;
}

/* ===== 下拉框 ===== */
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    border: 1px solid #E2E8F0;
    border-radius: 5px;
    background-color: #FFFFFF;
    selection-background-color: #EEF2FF;
    selection-color: #4F6EF7;
    padding: 3px; outline: none;
}

/* ===== 文本编辑区 ===== */
QTextEdit, QPlainTextEdit {
    padding: 5px 8px;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    background-color: #FFFFFF;
    font-size: 11px;
    selection-background-color: #4F6EF7;
    selection-color: #FFFFFF;
}
QTextEdit:focus, QPlainTextEdit:focus { border-color: #4F6EF7; }

/* ===== 表格 ===== */
QTableWidget {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background-color: #FFFFFF;
    gridline-color: #F1F5F9;
    font-size: 11px;
}
QTableWidget::item { padding: 5px 8px; min-height: 20px; }
QTableWidget::item:selected {
    background-color: #EEF2FF;
    color: #1E293B;
}
QHeaderView::section {
    background-color: #F8FAFC;
    padding: 6px 10px;
    border: none;
    border-bottom: 2px solid #E2E8F0;
    font-weight: 600;
    font-size: 11px;
    color: #475569;
}

/* ===== 标签 ===== */
QLabel#titleLabel {
    font-size: 18px;
    font-weight: 700;
    color: #0F172A;
}
QLabel#subtitleLabel {
    font-size: 11px;
    color: #64748B;
}
QLabel#statValue {
    font-size: 24px;
    font-weight: 700;
    color: #4F6EF7;
}
QLabel#statLabel {
    font-size: 10px;
    color: #94A3B8;
}
QLabel#sectionLabel {
    font-size: 13px;
    font-weight: 600;
    color: #1E293B;
    padding: 4px 0 2px 0;
}

/* ===== 分组框 ===== */
QGroupBox {
    font-weight: 600;
    font-size: 11px;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 10px;
    padding: 14px 12px 12px 12px;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #4F6EF7;
}

/* ===== 复选框 / 单选按钮 ===== */
QCheckBox, QRadioButton {
    spacing: 6px;
    font-size: 11px;
    min-height: 20px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 14px; height: 14px;
}
QCheckBox::indicator {
    border-radius: 3px;
    border: 2px solid #CBD5E1;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #4F6EF7;
    border-color: #4F6EF7;
}

/* ===== 信息标签（设置页等） ===== */
QLabel#infoLabel {
    font-size: 13px;
    color: #475569;
    min-height: 60px;
    padding: 8px 4px;
    background-color: transparent;
}
QLabel#infoLabel[state="error"] {
    color: #991B1B;
    font-weight: bold;
}
QLabel#offlineStatus {
    font-size: 12px;
    color: #64748B;
    min-height: 24px;
    padding: 4px 0;
}
QLabel#storageLabel {
    font-size: 12px;
    color: #1E293B;
    font-weight: 600;
    min-height: 26px;
    padding: 4px 0;
}
QLabel#storageValue {
    font-size: 12px;
    color: #334155;
    min-height: 26px;
    padding: 4px 0;
    font-family: Consolas, "Microsoft YaHei", monospace;
}
QLabel#statusText {
    font-size: 12px;
    color: #1E293B;
    min-height: 24px;
    padding: 4px 0;
}

/* ===== 弹窗对话框通用 ===== */
QLabel#dialogTitle {
    font-size: 15px;
    font-weight: bold;
    color: #0F172A;
    min-height: 24px;
}
QLabel#aboutUpdateLink {
    font-size: 13px;
    color: #4F6EF7;
    padding: 8px 10px;
    background: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 6px;
    min-height: 24px;
    font-family: Consolas, "Microsoft YaHei", monospace;
}
QLabel#dialogStatusLabel {
    font-size: 12px;
    font-weight: bold;
    min-height: 24px;
    color: #4F6EF7;
}
QLabel#dialogStatusLabel[state="success"] {
    color: #166534;
}
QLabel#dialogStatusLabel[state="failure"] {
    color: #991B1B;
}
QLabel#dialogStatusLabel[state="error"] {
    color: #d32f2f;
}
QPushButton#dialogCloseBtn {
    padding: 4px 20px;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    font-weight: bold;
    min-height: 30px;
    background-color: #FFFFFF;
    color: #334155;
}
QPushButton#dialogCloseBtn:hover {
    background-color: #F1F5F9;
    border-color: #4F6EF7;
}
QProgressBar#dialogProgressBar {
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    background: #F1F5F9;
    text-align: center;
    height: 22px;
}
QProgressBar#dialogProgressBar::chunk {
    background-color: #4F6EF7;
    border-radius: 5px;
}
QTextEdit#dialogLog {
    font-family: 'SF Mono', 'Consolas', 'Microsoft YaHei', monospace;
    font-size: 11px;
    padding: 6px;
    border-radius: 6px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
    color: #1E293B;
}
QTextEdit#dialogLog:focus {
    border-color: #4F6EF7;
}

/* ===== 设置页专用 ===== */
QLabel#maskedKey {
    font-family: Consolas, "Microsoft YaHei", monospace;
    font-size: 13px;
    color: #334155;
    min-height: 24px;
}
QLabel#apiKeyStatus {
    font-weight: bold;
    padding: 8px 10px;
    min-height: 24px;
}
QLabel#apiKeyStatus[state="configured"] {
    color: #2e7d32;
}
QLabel#apiKeyStatus[state="unconfigured"] {
    color: #e65100;
}
QLabel#testStatus {
    font-size: 12px;
    min-height: 24px;
    padding: 2px 0;
}
QLabel#testStatus[state="success"] {
    color: #2e7d32;
}
QLabel#testStatus[state="failure"] {
    color: #d32f2f;
}
QCheckBox#darkModeSwitch {
    font-size: 13px;
    font-weight: bold;
    min-height: 24px;
}

/* ===== 状态栏 ===== */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    font-size: 11px;
    color: #64748B;
    min-height: 22px;
    padding: 0 12px;
}

/* ===== 进度条 ===== */
QProgressBar {
    border: none;
    border-radius: 3px;
    background-color: #E2E8F0;
    height: 6px;
}
QProgressBar::chunk {
    background-color: #4F6EF7;
    border-radius: 3px;
}

/* ===== 滚动区域 ===== */
QScrollArea { border: none; background-color: transparent; }
/* 让滚动区内部 viewport 及内容容器透明，避免深浅色模式下露出白色/浅灰 */
QScrollArea > QWidget > QWidget { background-color: transparent; }
QScrollArea > QWidget#qt_scrollarea_viewport { background-color: transparent; }

/* ===== 滚动条 ===== */
QScrollBar:vertical {
    border: none; background: transparent;
    width: 5px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 2px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #94A3B8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    border: none; background: transparent;
    height: 5px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 2px;
    min-width: 28px;
}
QScrollBar::handle:horizontal:hover { background: #94A3B8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ===== 工具提示 ===== */
QToolTip {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 11px;
}

/* ===== 菜单（托盘右键菜单/下拉菜单） ===== */
QMenu {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #E2E8F0;
    padding: 6px;
}
QMenu::item {
    padding: 6px 26px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
}
QMenu::item:disabled {
    color: #94A3B8;
}
QMenu::separator {
    height: 1px;
    background: #E2E8F0;
    margin: 4px 8px;
}

/* ===== 分割线 ===== */
#divider { background-color: #E2E8F0; min-height: 1px; max-height: 1px; }
#verticalDivider { background-color: #E2E8F0; min-width: 1px; max-width: 1px; }

/* ===== 页面容器 ===== */
#pageContainer { background-color: #F4F6F9; }

/* ===== 卡片 ===== */
#cardFrame {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

/* ===== 今日概览专用 ===== */
QLabel#dateLabel {
    font-size: 16px;
    font-weight: bold;
    color: #1E293B;
    min-height: 24px;
}
QLabel#clockValue {
    font-size: 40px;
    font-weight: 700;
    color: #1E293B;
    font-family: 'SF Mono', 'Consolas', 'Microsoft YaHei', monospace;
}
QLabel#dateSmall {
    font-size: 12px;
    color: #94A3B8;
    min-height: 20px;
}
QLabel#countdownValue {
    font-size: 40px;
    font-weight: 700;
    color: #4F6EF7;
}
QLabel#countdownSub {
    font-size: 12px;
    color: #94A3B8;
    min-height: 20px;
}
QProgressBar#todayProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #E2E8F0;
}
QProgressBar#todayProgressBar::chunk {
    background-color: #4F6EF7;
    border-radius: 4px;
}
QTableWidget#todayTable {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    alternate-background-color: #F8FAFC;
}

QPushButton#offlineModeBtn {
    padding: 4px 14px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 12px;
    min-height: 28px;
}
QPushButton#offlineModeBtn[state="offline"] {
    background: #FEE2E2;
    color: #991B1B;
    border: 1px solid #FECACA;
}
QPushButton#offlineModeBtn[state="offline"]:hover {
    background: #FECACA;
}
QPushButton#offlineModeBtn[state="online"] {
    background: #DCFCE7;
    color: #166534;
    border: 1px solid #BBF7D0;
}
QPushButton#offlineModeBtn[state="online"]:hover {
    background: #BBF7D0;
}

/* ===== 考试管理页专用 ===== */
/* ExamEditDialog */
QLabel#examDialogTitle { font-size: 15px; font-weight: bold; }
QLabel#examPreviewLabel {
    padding: 6px 10px; background: #EEF2FF; border-radius: 6px;
    font-size: 12px; color: #4F6EF7; border: 1px solid #C7D2FE;
}

/* ReminderEditDialog */
QLabel#examReminderInfo {
    padding: 8px 12px; background: #EEF2FF; border-radius: 6px;
    border: 1px solid #C7D2FE;
}
QLabel#examReminderHeader { font-weight: bold; font-size: 13px; }
QLabel#examPreviewArea {
    padding: 8px 12px; background: #fafafa; border-radius: 6px;
    font-size: 12px; color: #555;
}
QFrame#examReminderRow {
    background: #fafafa; border: 1px solid #e8e8e8; border-radius: 6px;
}
QLabel#examTimeLabel { font-weight: bold; min-width: 45px; }
QLabel#examTimeLabel[type="start"] { color: #4F6EF7; }
QLabel#examTimeLabel[type="end"] { color: #EF4444; }
QLabel#examVoiceLabel { color: #666; font-size: 12px; }
QLabel#examAudioStatus {
    font-size: 12px; padding: 2px 6px; border-radius: 4px;
}
QLabel#examAudioStatus[state="custom"] {
    color: #22C55E; background: #f6ffed; border: 1px solid #b7eb8f;
}
QLabel#examAudioStatus[state="default"] {
    color: #666; background: #f5f5f5; border-radius: 4px;
}
QPushButton#examPickAudioBtn { font-size: 11px; padding: 2px 6px; }
QPushButton#examClearAudioBtn { font-size: 11px; padding: 2px 4px; color: #999; }
QPushButton#examPreviewBtn {
    font-size: 11px; padding: 2px 8px; color: #4F6EF7;
    border: 1px solid #C7D2FE; background: #EEF2FF; border-radius: 4px;
}
QPushButton#examPreviewBtn:hover { background: #DBE4FF; }
QLabel#examTtsLabel { color: #666; font-size: 12px; }
QLineEdit#examTtsInput { font-size: 12px; padding: 2px 6px; }

/* AddExamDialog */
QLabel#examAddTitle { font-size: 16px; font-weight: bold; }
QLabel#examAddPreview {
    padding: 6px 10px; background: #EEF2FF; border-radius: 6px;
    font-size: 12px; color: #4F6EF7; border: 1px solid #C7D2FE;
}
QFrame#examAddReminderRow {
    background: #fafafa; border: 1px solid #e8e8e8; border-radius: 6px;
}
QLabel#examAddTimeLabel { font-weight: bold; min-width: 45px; }
QLabel#examAddTimeLabel[type="start"] { color: #4F6EF7; }
QLabel#examAddTimeLabel[type="end"] { color: #EF4444; }
QLabel#examAddVoiceLabel { color: #666; font-size: 12px; }
QLabel#examAddAudioLabel {
    font-size: 12px; padding: 2px 6px; border-radius: 4px;
}
QLabel#examAddAudioLabel[state="custom"] {
    color: #22C55E; background: #f6ffed; border: 1px solid #b7eb8f;
}
QLabel#examAddAudioLabel[state="default"] {
    color: #666; background: #f5f5f5; border-radius: 4px;
}
QPushButton#examAddPickAudioBtn { font-size: 11px; padding: 2px 6px; }
QPushButton#examAddClearAudioBtn { font-size: 11px; padding: 2px 4px; color: #999; }
QPushButton#examAddPreviewBtn {
    font-size: 11px; padding: 2px 8px; color: #4F6EF7;
    border: 1px solid #C7D2FE; background: #EEF2FF; border-radius: 4px;
}
QPushButton#examAddPreviewBtn:hover { background: #DBE4FF; }
QLabel#examAddTtsLabel { color: #666; font-size: 12px; }
QLineEdit#examAddTtsInput { font-size: 12px; padding: 2px 6px; }

/* SingleReminderEditDialog */
QLabel#examSingleTitle { font-size: 15px; font-weight: bold; }
QLabel#examSingleInfo {
    padding: 6px 10px; background: #EEF2FF; border-radius: 6px;
    font-size: 12px; border: 1px solid #C7D2FE;
}
QLabel#examSingleAudioLabel {
    font-size: 12px; padding: 4px 8px; border-radius: 4px;
}
QLabel#examSingleAudioLabel[state="custom"] {
    color: #22C55E; background: #f6ffed; border: 1px solid #b7eb8f;
}
QLabel#examSingleAudioLabel[state="default"] {
    color: #666; background: #f5f5f5; border-radius: 4px;
}
QPushButton#examSingleClearBtn { color: #999; }
QLabel#examSingleTtsLabel { color: #666; font-size: 12px; }
QLineEdit#examSingleTtsInput { font-size: 12px; padding: 2px 6px; }
QLabel#examSinglePreview {
    padding: 6px 10px; background: #EEF2FF; border-radius: 6px;
    font-size: 12px; color: #4F6EF7; border: 1px solid #C7D2FE;
}

/* ===== 弹窗 (QDialog / 自建对话框) ===== */
QDialog {
    background-color: #FFFFFF;
    color: #1E293B;
}

/* BroadcastPopup */
QDialog#broadcastPopup {
    background: #FFFFFF;
    border: 2px solid #4F6EF7;
    border-radius: 14px;
}

/* ===== 消息框 (QMessageBox) ===== */
QMessageBox {
    background-color: #FFFFFF;
    color: #1E293B;
}
QMessageBox QLabel {
    color: #1E293B;
    background-color: transparent;
}
QMessageBox QPushButton {
    min-height: 26px;
    padding: 4px 12px;
}
QLabel#broadcastTitle {
    font-size: 15px; font-weight: bold; color: #4F6EF7;
}
QFrame#broadcastSep { background: #E2E8F0; max-height: 1px; }
QLabel#broadcastContent {
    font-size: 13px; color: #333; padding: 10px 12px;
    background: #EEF2FF; border-radius: 8px; border: 1px solid #C7D2FE;
}
QLabel#broadcastHint { font-size: 12px; color: #999; }

/* ExamPage */
QLabel#examPageTitle { font-size: 18px; font-weight: bold; }
QLabel#examPageStatus { color: #999; font-size: 12px; padding: 2px 0; }
QFrame#examPageCardFrame {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
}
QLabel#examPageSectionLabel { font-size: 14px; font-weight: bold; }
QLabel#examPageCountLabel { color: #999; font-size: 11px; }
QLabel#examPageCardSubject {
    font-size: 12px; font-weight: bold; color: #1d1d1f;
}
QLabel#examPageCardDetail { color: #666; font-size: 11px; }
QLabel#examPageCardRemindSummary { color: #4F6EF7; font-size: 11px; }
QLabel#examPageCardRemindSummary[state="empty"] { color: #999; font-size: 11px; }
QLabel#examPageCardTime { color: #888; font-size: 10px; }
QLabel#examPageReminderTitle {
    padding: 6px 10px; background: #EEF2FF; border-radius: 6px;
    font-size: 12px; color: #4F6EF7; border: 1px solid #C7D2FE;
}
QLabel#examPageReminderTitle[state="empty"] {
    padding: 8px 12px; background: #EEF2FF; border-radius: 8px;
    font-size: 13px; color: #4F6EF7; border: 1px solid #C7D2FE;
}
QLabel#examPageEmptyLabel { color: #999; font-size: 12px; padding: 16px; }
QLabel#examPageReminderLabel {
    font-size: 11px; font-weight: bold; color: #1d1d1f;
}
QLabel#examPageReminderLabel[state="disabled"] {
    font-size: 11px; font-weight: bold; color: #aaa;
}
QLabel#examPageReminderTime { color: #4F6EF7; font-size: 11px; }
QLabel#examPageAudioLabel { font-size: 11px; }
QLabel#examPageAudioLabel[state="custom"] { color: #22C55E; }
QLabel#examPageAudioLabel[state="default"] { color: #888; }
QScrollArea#examPageScroll { background: transparent; }

/* Status badge */
QLabel#examPageCardStatus {
    padding: 1px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
}
QLabel#examPageCardStatus[state="即将开始"] {
    background: #DCFCE7; color: #166534;
}
QLabel#examPageCardStatus[state="进行中"] {
    background: #DBEAFE; color: #1E40AF;
}
QLabel#examPageCardStatus[state="已结束"] {
    background: #FEE2E2; color: #991B1B;
}
QLabel#examPageCardStatus[state="—"] {
    background: #f5f5f5; color: #999;
}

/* Toggle button */
QPushButton#examPageToggleBtn {
    padding: 1px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;
    border: none; min-height: 20px;
}
QPushButton#examPageToggleBtn[state="enabled"] {
    background: #DCFCE7; color: #166534;
}
QPushButton#examPageToggleBtn[state="disabled"] {
    background: #FEE2E2; color: #991B1B;
}

/* Reminder card */
QFrame#reminderCard[state="disabled"] {
    background: #fafafa; border: 1px solid #e0e0e0;
    border-radius: 10px; padding: 14px;
}
QFrame#reminderCard[state="disabled"]:hover {
    border-color: #ccc; background: #f5f5f5;
}
QFrame#reminderCard[state="enabled"] {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 10px;
}
QFrame#reminderCard[state="enabled"]:hover {
    border-color: #4F6EF7; background: #F8FAFF;
}

/* ExamCard */
QFrame#examCard {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;
    padding: 10px;
}
QFrame#examCard:hover {
    border-color: #4F6EF7; background: #F8FAFF;
}
QFrame#examCard[selected="true"] {
    border-color: #4F6EF7; border-width: 2px; background: #EEF2FF;
}

/* AI checkbox */
QCheckBox#examAiCheckbox { font-size: 11px; }

/* AddExamDialog QGroupBox */
QGroupBox#examAddGroup {
    font-weight: bold; font-size: 12px; border: 1px solid #E2E8F0;
    border-radius: 8px; margin-top: 8px; padding-top: 14px;
}
QGroupBox#examAddGroup::title {
    subcontrol-origin: margin; left: 12px; padding: 0 6px;
}
QGroupBox#examAddReminderGroup {
    font-weight: bold; font-size: 12px; border: 1px solid #E2E8F0;
    border-radius: 8px; margin-top: 8px; padding-top: 14px;
}
QGroupBox#examAddReminderGroup::title {
    subcontrol-origin: margin; left: 12px; padding: 0 6px;
}

/* ===== 启动页 (SplashScreen) — Visual Studio 风格 ===== */
#splashScreenRoot {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}
/* 背景图层：图片由 QPixmap 铺满；遮罩在浅色下透明，不遮挡背景 */
QLabel#splashBg { background-color: transparent; }
QLabel#splashBgOverlay { background-color: transparent; }
QLabel#splashTitle {
    font-size: 32px;
    font-weight: 700;
    color: #1E293B;
    letter-spacing: 2px;
}
QLabel#splashVersion {
    font-size: 13px;
    color: #94A3B8;
    letter-spacing: 1px;
}
QProgressBar#splashProgress {
    border: none;
    border-radius: 1px;
    background-color: #E2E8F0;
}
QProgressBar#splashProgress::chunk {
    background-color: #4F6EF7;
    border-radius: 1px;
}
QLabel#splashStatus {
    font-size: 11px;
    color: #94A3B8;
}

/* ===== 关于页 (AboutPage) ===== */
QLabel#aboutAppTitle {
    font-size: 20px; font-weight: bold; color: #1E293B;
    min-height: 32px;
}
#aboutDivider {
    background-color: #E2E8F0;
    min-height: 1px; max-height: 1px;
}
QLabel#aboutInfoRow {
    font-size: 13px; color: #475569;
    min-height: 24px;
}
QLabel#aboutWarning {
    font-size: 12px; min-height: 28px;
    padding: 8px 12px; border-radius: 6px;
}
QLabel#aboutWarning[state="warning"] {
    color: #991B1B; background: #FEE2E2;
    border: 1px solid #FECACA;
}
QLabel#aboutUpdateInfo {
    font-size: 12px; color: #94A3B8;
    min-height: 20px;
}
QPushButton#aboutRefreshBtn {
    min-height: 28px; padding: 4px 16px;
}
QPushButton#aboutCloseBtn {
    min-height: 28px; padding: 4px 16px;
}
QTextEdit#logText {
    font-family: 'SF Mono', 'Consolas', 'Microsoft YaHei', monospace;
    font-size: 11px; padding: 6px; border-radius: 6px;
    border: 1px solid #CBD5E1; background-color: #F8FAFC;
    color: #1E293B;
}

/* ===== API Key 弹窗 ===== */
QLineEdit#apiKeyInput {
    font-size: 13px; padding: 6px 10px;
    min-height: 28px;
}
QPushButton#aboutRefreshBtn { min-height: 28px; padding: 4px 16px; }
QPushButton#aboutCloseBtn { min-height: 28px; padding: 4px 16px; }
QStatusBar#statusBar { background-color: #FFFFFF; border-top: 1px solid #E2E8F0; }
"""


# ─────────────────────────────────────────────────────
#  深色模式样式表
# ─────────────────────────────────────────────────────

DARK_STYLESHEET = """
/* ===== 深色模式 — 设计令牌 ===== */
/* 主色: 靛蓝 #6366F1 */
/* 背景: 深灰 #1E1E2E */
/* 卡片背景: #2A2A3E */

QMainWindow { background-color: #1E1E2E; }
#centralWidget { background-color: #1E1E2E; }
QDialog {
    background-color: #2A2A3E;
    color: #E2E8F0;
}
/* ===== 消息框 (QMessageBox) 深色 ===== */
QMessageBox {
    background-color: #2A2A3E;
    color: #E2E8F0;
}
QMessageBox QLabel {
    color: #E2E8F0;
    background-color: transparent;
}
QWidget {
    font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
    font-size: 11px;
    color: #E2E8F0;
}
QFrame {
    color: #E2E8F0;
}

#titleBar {
    background-color: #2A2A3E;
    border-bottom: 1px solid #3A3A52;
}
QLabel#titleBarIcon { color: #818CF8; }
QLabel#titleBarTitle { color: #F1F5F9; }
QLabel#titleBarOfflineTag {
    color: #FCA5A5; background: #4C1D1D;
    border: 1px solid #7F1D1D;
}
QPushButton#titleBarMinBtn {
    color: #94A3B8;
}
QPushButton#titleBarMinBtn:hover {
    background: #363650; color: #F1F5F9;
}
QPushButton#titleBarQuitBtn {
    color: #F87171;
}
QPushButton#titleBarQuitBtn:hover {
    background: #4C1D1D; color: #FCA5A5;
}
QPushButton#titleBarCloseBtn {
    color: #94A3B8;
}
QPushButton#titleBarCloseBtn:hover {
    background: #DC2626; color: #FFFFFF;
}
QPushButton#titleBarFullscreenBtn {
    background: #3B3B5C; border: 1px solid #4F4F78; color: #A5B4FC;
}
QPushButton#titleBarFullscreenBtn:hover {
    background: #46466B; border-color: #818CF8; color: #C7D2FE;
}
QLabel#statusLabel {
    color: #94A3B8;
}

/* 全屏模式：无声提示层（深色） */
#fullscreenTip {
    background-color: rgba(30, 30, 46, 0.94);
    color: #F1F5F9; font-size: 13px; font-weight: 600;
    border: 1px solid #4F4F78; border-radius: 8px; padding: 12px 20px;
}
/* 全屏模式：退出确认对话框（深色） */
QDialog#fullscreenConfirmDlg {
    background-color: #1E1E2E; border: 1px solid #3A3A52; border-radius: 8px;
}
QLabel#fullscreenConfirmMsg { color: #F1F5F9; }
QLabel#fullscreenConfirmHint { color: #94A3B8; }
/* 无声自绘 Toast（深色下与浅色一致，深色胶囊 + 白字仍清晰） */
#toast {
    background-color: rgba(26, 28, 44, 0.97);
    border: 1px solid #4F4F78;
    border-radius: 8px;
}
QLabel#toastText {
    color: #F1F5F9; font-size: 12px;
}
QLabel#toastIcon {
    font-size: 13px; font-weight: bold;
}
QLabel#toastIcon[kind="info"] { color: #93C5FD; }
QLabel#toastIcon[kind="success"] { color: #4ADE80; }
QLabel#toastIcon[kind="warning"] { color: #FBBF24; }
QLabel#toastIcon[kind="error"] { color: #F87171; }
QPushButton#primaryBtn {
    background: #4F6EF7; color: #FFFFFF; border: none; border-radius: 4px;
    padding: 5px 12px; font-size: 12px; font-weight: 600;
}
QPushButton#primaryBtn:hover { background: #4338CA; }
QPushButton#cancelBtn {
    background: #2A2A3E; color: #E2E8F0; border: 1px solid #3A3A52;
    border-radius: 4px; padding: 5px 12px; font-size: 12px;
}
QPushButton#cancelBtn:hover { background: #363650; }

#navFrame {
    background-color: #2A2A3E;
    border-right: 1px solid #3A3A52;
}
#navList {
    background-color: transparent;
    border: none; outline: none;
    padding: 4px 8px;
}
#navList::item {
    padding: 7px 12px;
    border-radius: 6px;
    margin: 2px 3px;
    font-size: 12px;
    color: #94A3B8;
}
#navList::item:selected {
    background-color: transparent;
    color: #818CF8;
    font-weight: 600;
}
#navList::item:hover:!selected {
    background-color: #363650;
}
/* 侧边栏选中高亮滑块（背景层，由几何动画驱动平滑滑动） */
#navHighlight {
    background-color: #3B3B5C;
    border-radius: 6px;
}

QPushButton {
    padding: 4px 12px;
    border-radius: 5px;
    font-size: 11px;
    border: 1px solid #3A3A52;
    background-color: #2A2A3E;
    color: #E2E8F0;
    min-height: 26px;
}
QPushButton:hover {
    border-color: #6366F1;
    color: #818CF8;
    background-color: #32324A;
}
QPushButton:pressed {
    background-color: #3B3B5C;
}
QPushButton:disabled {
    color: #64748B;
    border-color: #3A3A52;
    background-color: #262636;
}

QPushButton#accentBtn {
    background-color: #6366F1;
    color: #FFFFFF;
    border: none;
    font-weight: 600;
    min-height: 30px;
    padding: 5px 18px;
}
QPushButton#accentBtn:hover { background-color: #4F46E5; }
QPushButton#accentBtn:pressed { background-color: #4338CA; }
QPushButton#accentBtn:disabled {
    background-color: #4C4C6E;
    color: #94A3B8;
}

QPushButton#dangerBtn {
    color: #F87171;
    border-color: #7F1D1D;
    min-height: 26px;
}
QPushButton#dangerBtn:hover {
    background-color: #3B1A1A;
    border-color: #EF4444;
}

QPushButton#tagBtn {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    border: 1px solid #3A3A52;
    background-color: #2A2A3E;
    color: #94A3B8;
    min-height: 22px;
}
QPushButton#tagBtn:hover {
    border-color: #6366F1;
    color: #818CF8;
    background-color: #32324A;
}
QPushButton#tagBtn[active="true"] {
    background-color: #6366F1;
    color: #FFFFFF;
    border-color: #6366F1;
}

QPushButton#tableActionBtn {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    border: 1px solid #3A3A52;
    background-color: #2A2A3E;
    color: #94A3B8;
    min-height: 22px;
}
QPushButton#tableActionBtn:hover {
    border-color: #6366F1;
    color: #818CF8;
    background-color: #32324A;
}

QPushButton#tableDeleteBtn {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    border: 1px solid #7F1D1D;
    background-color: #2A2A3E;
    color: #F87171;
    min-height: 22px;
}
QPushButton#tableDeleteBtn:hover {
    background-color: #3B1A1A;
    border-color: #EF4444;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    padding: 4px 8px;
    border: 1px solid #3A3A52;
    border-radius: 5px;
    background-color: #1E1E2E;
    color: #E2E8F0;
    font-size: 11px;
    min-height: 20px;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #6366F1;
    border-width: 1.5px;
    padding: 4.5px 9.5px;
    background-color: #222238;
}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background-color: #262636;
    color: #64748B;
}

QDateEdit, QTimeEdit, QDateTimeEdit {
    padding: 4px 8px;
    border: 1px solid #3A3A52;
    border-radius: 5px;
    background-color: #1E1E2E;
    color: #E2E8F0;
    font-size: 11px;
    min-height: 20px;
}
QDateEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus {
    border-color: #6366F1;
    border-width: 1.5px;
    padding: 4.5px 9.5px;
}
QDateEdit::drop-down, QTimeEdit::drop-down, QDateTimeEdit::drop-down {
    border: none; width: 20px;
}

QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    border: 1px solid #3A3A52;
    border-radius: 5px;
    background-color: #2A2A3E;
    selection-background-color: #3B3B5C;
    selection-color: #818CF8;
    padding: 3px; outline: none;
}

QTextEdit, QPlainTextEdit {
    padding: 5px 8px;
    border: 1px solid #3A3A52;
    border-radius: 5px;
    background-color: #1E1E2E;
    color: #E2E8F0;
    font-size: 11px;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
}
QTextEdit:focus, QPlainTextEdit:focus { border-color: #6366F1; }

QTableWidget {
    border: 1px solid #3A3A52;
    border-radius: 8px;
    background-color: #2A2A3E;
    gridline-color: #3A3A52;
    color: #E2E8F0;
    font-size: 11px;
}
QTableWidget::item { padding: 5px 8px; min-height: 20px; }
QTableWidget::item:selected {
    background-color: #3B3B5C;
    color: #E2E8F0;
}
QHeaderView::section {
    background-color: #1E1E2E;
    padding: 6px 10px;
    border: none;
    border-bottom: 2px solid #3A3A52;
    font-weight: 600;
    font-size: 11px;
    color: #94A3B8;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: 700;
    color: #F1F5F9;
}
QLabel#subtitleLabel {
    font-size: 11px;
    color: #94A3B8;
}
QLabel#statValue {
    font-size: 24px;
    font-weight: 700;
    color: #818CF8;
}
QLabel#statLabel {
    font-size: 10px;
    color: #64748B;
}
QLabel#sectionLabel {
    font-size: 13px;
    font-weight: 600;
    color: #E2E8F0;
    padding: 4px 0 2px 0;
}

QGroupBox {
    font-weight: 600;
    font-size: 11px;
    border: 1px solid #3A3A52;
    border-radius: 8px;
    margin-top: 10px;
    padding: 14px 12px 12px 12px;
    background-color: #2A2A3E;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #818CF8;
}

/* 深色模式：通用列表控件深色化（template_page 等未设对象名的列表） */
QListWidget {
    background-color: #2A2A3E;
    color: #E2E8F0;
    border: 1px solid #3A3A52;
    border-radius: 8px;
    outline: none;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 6px;
    margin: 1px 2px;
    color: #E2E8F0;
}
QListWidget::item:selected {
    background-color: #3B3B5C;
    color: #818CF8;
}
QListWidget::item:hover:!selected {
    background-color: #32324A;
}

QCheckBox, QRadioButton {
    spacing: 6px;
    font-size: 11px;
    min-height: 20px;
    color: #E2E8F0;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 14px; height: 14px;
}
QCheckBox::indicator {
    border-radius: 3px;
    border: 2px solid #3A3A52;
    background-color: #1E1E2E;
}
QCheckBox::indicator:checked {
    background-color: #6366F1;
    border-color: #6366F1;
}

QSlider::groove:horizontal {
    border: 1px solid #3A3A52;
    height: 6px;
    background: #1E1E2E;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #6366F1;
    border: none;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #4F46E5;
}
QSlider::sub-page:horizontal {
    background: #6366F1;
    border-radius: 3px;
}

QDialogButtonBox QPushButton {
    min-height: 28px;
    padding: 4px 16px;
}

QLabel#infoLabel {
    font-size: 13px;
    color: #CBD5E1;
    min-height: 60px;
    padding: 8px 4px;
    background-color: transparent;
}
QLabel#infoLabel[state="error"] {
    color: #FCA5A5;
    font-weight: bold;
}
QLabel#offlineStatus {
    font-size: 12px;
    color: #94A3B8;
    min-height: 24px;
    padding: 4px 0;
}
QLabel#storageLabel {
    font-size: 12px;
    color: #F1F5F9;
    font-weight: 600;
    min-height: 26px;
    padding: 4px 0;
}
QLabel#storageValue {
    font-size: 12px;
    color: #CBD5E1;
    min-height: 26px;
    padding: 4px 0;
    font-family: Consolas, "Microsoft YaHei", monospace;
}
QLabel#statusText {
    font-size: 12px;
    color: #E2E8F0;
    min-height: 24px;
    padding: 4px 0;
}

/* ===== 弹窗对话框通用（深色） ===== */
QLabel#dialogTitle {
    font-size: 15px;
    font-weight: bold;
    color: #F1F5F9;
    min-height: 24px;
}
QLabel#aboutUpdateLink {
    font-size: 13px;
    color: #818CF8;
    padding: 8px 10px;
    background: #262636;
    border: 1px solid #3A3A52;
    border-radius: 6px;
    min-height: 24px;
    font-family: Consolas, "Microsoft YaHei", monospace;
}
QLabel#dialogStatusLabel {
    font-size: 12px;
    font-weight: bold;
    min-height: 24px;
    color: #818CF8;
}
QLabel#dialogStatusLabel[state="success"] {
    color: #86EFAC;
}
QLabel#dialogStatusLabel[state="failure"] {
    color: #FCA5A5;
}
QLabel#dialogStatusLabel[state="error"] {
    color: #F87171;
}
QPushButton#dialogCloseBtn {
    padding: 4px 20px;
    border: 1px solid #3A3A52;
    border-radius: 6px;
    font-weight: bold;
    min-height: 30px;
    background-color: #2A2A3E;
    color: #E2E8F0;
}
QPushButton#dialogCloseBtn:hover {
    background-color: #363650;
    border-color: #6366F1;
}
QProgressBar#dialogProgressBar {
    border: 1px solid #3A3A52;
    border-radius: 6px;
    background: #1E1E2E;
    text-align: center;
    height: 22px;
}
QProgressBar#dialogProgressBar::chunk {
    background-color: #6366F1;
    border-radius: 5px;
}
QTextEdit#dialogLog {
    font-family: 'SF Mono', 'Consolas', 'Microsoft YaHei', monospace;
    font-size: 11px;
    padding: 6px;
    border-radius: 6px;
    border: 1px solid #3A3A52;
    background-color: #1E1E2E;
    color: #E2E8F0;
}
QTextEdit#dialogLog:focus {
    border-color: #6366F1;
}

/* ===== 设置页专用（深色） ===== */
QLabel#maskedKey {
    font-family: Consolas, "Microsoft YaHei", monospace;
    font-size: 13px;
    color: #CBD5E1;
    min-height: 24px;
}
QLabel#apiKeyStatus {
    font-weight: bold;
    padding: 8px 10px;
    min-height: 24px;
}
QLabel#apiKeyStatus[state="configured"] {
    color: #86EFAC;
}
QLabel#apiKeyStatus[state="unconfigured"] {
    color: #FBBF24;
}
QLabel#testStatus {
    font-size: 12px;
    min-height: 24px;
    padding: 2px 0;
}
QLabel#testStatus[state="success"] {
    color: #86EFAC;
}
QLabel#testStatus[state="failure"] {
    color: #F87171;
}
QCheckBox#darkModeSwitch {
    font-size: 13px;
    font-weight: bold;
    min-height: 24px;
    color: #E2E8F0;
}

QStatusBar {
    background-color: #2A2A3E;
    border-top: 1px solid #3A3A52;
    font-size: 11px;
    color: #94A3B8;
    min-height: 22px;
    padding: 0 12px;
}

QProgressBar {
    border: none;
    border-radius: 3px;
    background-color: #3A3A52;
    height: 6px;
}
QProgressBar::chunk {
    background-color: #6366F1;
    border-radius: 3px;
}

QScrollArea { border: none; background-color: transparent; }
/* 深色模式：让滚动区内部 viewport 及内容容器透明，修复白色背景 */
QScrollArea > QWidget > QWidget { background-color: transparent; }
QScrollArea > QWidget#qt_scrollarea_viewport { background-color: transparent; }

QScrollBar:vertical {
    border: none;
    background: #24243A;      /* 细腻导轨底色，避免透明导致的暗色斑状 */
    width: 8px;
    margin: 2px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #7A7AA8;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #9494C0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    border: none;
    background: #24243A;
    height: 8px;
    margin: 2px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #7A7AA8;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #9494C0; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QToolTip {
    background-color: #1E1E2E;
    color: #E2E8F0;
    border: 1px solid #3A3A52;
    border-radius: 5px;
    padding: 6px 10px;
    font-size: 11px;
}

/* 菜单深色覆盖：背景随主题联动，文字用浅色保证对比（避免深底深字） */
QMenu {
    background-color: #262638;
    color: #E2E8F0;
    border: 1px solid #3A3A52;
    padding: 6px;
}
QMenu::item:selected {
    background-color: #3A3A52;
    color: #FFFFFF;
}
QMenu::item:disabled {
    color: #6B6B87;
}
QMenu::separator {
    background: #3A3A52;
}

#divider { background-color: #3A3A52; min-height: 1px; max-height: 1px; }
#verticalDivider { background-color: #3A3A52; min-width: 1px; max-width: 1px; }

#pageContainer { background-color: #1E1E2E; }

#cardFrame {
    background-color: #2A2A3E;
    border: 1px solid #3A3A52;
    border-radius: 8px;
}

/* ===== 今日概览专用（深色） ===== */
QLabel#dateLabel {
    font-size: 16px;
    font-weight: bold;
    color: #F1F5F9;
    min-height: 24px;
}
QLabel#clockValue {
    font-size: 40px;
    font-weight: 700;
    color: #F1F5F9;
    font-family: 'SF Mono', 'Consolas', 'Microsoft YaHei', monospace;
}
QLabel#dateSmall {
    font-size: 12px;
    color: #64748B;
    min-height: 20px;
}
QLabel#countdownValue {
    font-size: 40px;
    font-weight: 700;
    color: #818CF8;
}
QLabel#countdownSub {
    font-size: 12px;
    color: #64748B;
    min-height: 20px;
}
QProgressBar#todayProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #3A3A52;
}
QProgressBar#todayProgressBar::chunk {
    background-color: #6366F1;
    border-radius: 4px;
}
QTableWidget#todayTable {
    border: 1px solid #3A3A52;
    border-radius: 8px;
    background-color: #2A2A3E;
    alternate-background-color: #262636;
}
QLabel#sectionLabel {
    color: #E2E8F0;
}

QPushButton#offlineModeBtn {
    padding: 4px 14px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 12px;
    min-height: 28px;
}
QPushButton#offlineModeBtn[state="offline"] {
    background: #4C1D1D;
    color: #FCA5A5;
    border: 1px solid #7F1D1D;
}
QPushButton#offlineModeBtn[state="offline"]:hover {
    background: #5C2424;
}
QPushButton#offlineModeBtn[state="online"] {
    background: #14532D;
    color: #86EFAC;
    border: 1px solid #166534;
}
QPushButton#offlineModeBtn[state="online"]:hover {
    background: #166534;
}

/* ===== 考试管理页专用（深色） ===== */
/* ExamEditDialog */
QLabel#examPreviewLabel {
    background: #3B3B5C; border: 1px solid #4C4C6E;
    color: #818CF8;
}
/* ReminderEditDialog */
QLabel#examReminderInfo {
    background: #3B3B5C; border: 1px solid #4C4C6E;
    color: #E2E8F0;
}
QLabel#examPreviewArea {
    background: #262636; border: 1px solid #3A3A52;
    color: #CBD5E1;
}
QFrame#examReminderRow {
    background: #262636; border: 1px solid #3A3A52;
}
QLabel#examVoiceLabel { color: #94A3B8; }
QLabel#examAudioStatus[state="custom"] {
    color: #86EFAC; background: #14532D; border: 1px solid #166534;
}
QLabel#examAudioStatus[state="default"] {
    color: #94A3B8; background: #262636;
}
QPushButton#examClearAudioBtn { color: #64748B; }
QPushButton#examPreviewBtn {
    color: #818CF8; border: 1px solid #4C4C6E;
    background: #3B3B5C;
}
QPushButton#examPreviewBtn:hover { background: #4C4C6E; }
QLabel#examTtsLabel { color: #94A3B8; }

/* AddExamDialog */
QLabel#examAddPreview {
    background: #3B3B5C; border: 1px solid #4C4C6E;
    color: #818CF8;
}
QFrame#examAddReminderRow {
    background: #262636; border: 1px solid #3A3A52;
}
QLabel#examAddVoiceLabel { color: #94A3B8; }
QLabel#examAddAudioLabel[state="custom"] {
    color: #86EFAC; background: #14532D; border: 1px solid #166534;
}
QLabel#examAddAudioLabel[state="default"] {
    color: #94A3B8; background: #262636;
}
QPushButton#examAddClearAudioBtn { color: #64748B; }
QPushButton#examAddPreviewBtn {
    color: #818CF8; border: 1px solid #4C4C6E;
    background: #3B3B5C;
}
QPushButton#examAddPreviewBtn:hover { background: #4C4C6E; }
QLabel#examAddTtsLabel { color: #94A3B8; }

/* SingleReminderEditDialog */
QLabel#examSingleInfo {
    background: #3B3B5C; border: 1px solid #4C4C6E;
    color: #E2E8F0;
}
QLabel#examSingleAudioLabel[state="custom"] {
    color: #86EFAC; background: #14532D; border: 1px solid #166534;
}
QLabel#examSingleAudioLabel[state="default"] {
    color: #94A3B8; background: #262636;
}
QPushButton#examSingleClearBtn { color: #64748B; }
QLabel#examSingleTtsLabel { color: #94A3B8; }
QLabel#examSinglePreview {
    background: #3B3B5C; border: 1px solid #4C4C6E;
    color: #818CF8;
}

/* BroadcastPopup（深色） */
QDialog#broadcastPopup {
    background: #2A2A3E;
    border: 2px solid #6366F1;
}
QLabel#broadcastTitle { color: #818CF8; }
QFrame#broadcastSep { background: #3A3A52; }
QLabel#broadcastContent {
    color: #E2E8F0; padding: 10px 12px;
    background: #3B3B5C; border: 1px solid #4C4C6E;
}
QLabel#broadcastHint { color: #64748B; }

/* ExamPage（深色） */
QLabel#examPageStatus { color: #64748B; }
QFrame#examPageCardFrame {
    background: #2A2A3E; border: 1px solid #3A3A52;
}
QLabel#examPageCountLabel { color: #64748B; }
QLabel#examPageCardSubject { color: #F1F5F9; }
QLabel#examPageCardDetail { color: #94A3B8; }
QLabel#examPageCardRemindSummary { color: #818CF8; }
QLabel#examPageCardRemindSummary[state="empty"] { color: #64748B; }
QLabel#examPageCardTime { color: #64748B; }
QLabel#examPageReminderTitle {
    padding: 6px 10px; background: #3B3B5C; border-radius: 6px;
    font-size: 12px; color: #818CF8; border: 1px solid #4C4C6E;
}
QLabel#examPageReminderTitle[state="empty"] {
    padding: 8px 12px; background: #3B3B5C; border-radius: 8px;
    font-size: 13px; color: #818CF8; border: 1px solid #4C4C6E;
}
QLabel#examPageEmptyLabel { color: #64748B; }
QLabel#examPageReminderLabel { color: #F1F5F9; }
QLabel#examPageReminderLabel[state="disabled"] { color: #64748B; }
QLabel#examPageReminderTime { color: #818CF8; }
QLabel#examPageAudioLabel[state="custom"] { color: #86EFAC; }
QLabel#examPageAudioLabel[state="default"] { color: #64748B; }

/* Status badge（深色） */
QLabel#examPageCardStatus[state="即将开始"] {
    background: #14532D; color: #86EFAC;
}
QLabel#examPageCardStatus[state="进行中"] {
    background: #1E3A5F; color: #93C5FD;
}
QLabel#examPageCardStatus[state="已结束"] {
    background: #4C1D1D; color: #FCA5A5;
}
QLabel#examPageCardStatus[state="—"] {
    background: #262636; color: #64748B;
}

/* Toggle button（深色） */
QPushButton#examPageToggleBtn[state="enabled"] {
    background: #14532D; color: #86EFAC;
}
QPushButton#examPageToggleBtn[state="disabled"] {
    background: #4C1D1D; color: #FCA5A5;
}

/* Reminder card（深色） */
QFrame#reminderCard[state="disabled"] {
    background: #262636; border: 1px solid #3A3A52;
}
QFrame#reminderCard[state="disabled"]:hover {
    border-color: #555; background: #2A2A3E;
}
QFrame#reminderCard[state="enabled"] {
    background: #2A2A3E; border: 1px solid #3A3A52;
}
QFrame#reminderCard[state="enabled"]:hover {
    border-color: #6366F1; background: #32324A;
}

/* ExamCard（深色） */
QFrame#examCard {
    background: #2A2A3E; border: 1px solid #3A3A52;
}
QFrame#examCard:hover {
    border-color: #6366F1; background: #32324A;
}
QFrame#examCard[selected="true"] {
    border-color: #6366F1; border-width: 2px; background: #3B3B5C;
}

/* AddExamDialog QGroupBox（深色） */
QGroupBox#examAddGroup {
    border: 1px solid #3A3A52;
}
QGroupBox#examAddReminderGroup {
    border: 1px solid #3A3A52;
}

/* 补全 exam_page 中 GLOBAL 有定义但 DARK 缺少的规则 */
QLabel#examDialogTitle { color: #F1F5F9; }
QLabel#examPageTitle { color: #F1F5F9; }
QLabel#examReminderHeader { color: #F1F5F9; }
QLabel#examSingleTitle { color: #F1F5F9; }
QLabel#examAddTitle { color: #F1F5F9; }
QLabel#examPageSectionLabel { color: #F1F5F9; }
QLabel#examTimeLabel[type="start"] { color: #818CF8; }
QLabel#examTimeLabel[type="end"] { color: #F87171; }
QLabel#examAddTimeLabel[type="start"] { color: #818CF8; }
QLabel#examAddTimeLabel[type="end"] { color: #F87171; }
QLabel#examAudioStatus { color: #94A3B8; }
QLabel#examAddAudioLabel { color: #94A3B8; }
QLabel#examSingleAudioLabel { color: #94A3B8; }
QLabel#examPageAudioLabel { color: #94A3B8; }
QLabel#examPageAudioLabel[state="default"] { color: #64748B; }
QCheckBox#examAiCheckbox { color: #E2E8F0; }
QLabel#aboutWarning { color: #CBD5E1; }
QFrame#reminderCard[state="disabled"]:hover { border-color: #555; background: #2A2A3E; }

/* ===== 启动页（深色） — Visual Studio 风格 ===== */
#splashScreenRoot {
    background-color: #1E1E2E;
    border: 1px solid #3A3A52;
}
/* 深色：背景图被半透明深色遮罩压暗，浅色标题仍清晰可读 */
QLabel#splashBg { background-color: transparent; }
QLabel#splashBgOverlay {
    background-color: rgba(20, 22, 40, 0.5);
}
QLabel#splashTitle { color: #F1F5F9; }
QLabel#splashVersion { color: #64748B; }
QProgressBar#splashProgress {
    background-color: #3A3A52;
}
QProgressBar#splashProgress::chunk {
    background-color: #6366F1;
}
QLabel#splashStatus { color: #64748B; }

/* ===== 关于页（深色） ===== */
QLabel#aboutAppTitle { color: #F1F5F9; }
#aboutDivider { background-color: #3A3A52; }
QLabel#aboutInfoRow { color: #CBD5E1; }
QLabel#aboutWarning[state="warning"] {
    color: #FCA5A5; background: #4C1D1D;
    border: 1px solid #7F1D1D;
}
QLabel#aboutUpdateInfo { color: #64748B; }
QTextEdit#logText {
    border: 1px solid #3A3A52; background-color: #1E1E2E;
    color: #E2E8F0;
}
QPushButton#aboutRefreshBtn { color: #E2E8F0; border-color: #3A3A52; }
QPushButton#aboutRefreshBtn:hover { border-color: #6366F1; color: #818CF8; }
QPushButton#aboutCloseBtn { color: #E2E8F0; border-color: #3A3A52; }
QPushButton#aboutCloseBtn:hover { border-color: #6366F1; }
QLineEdit#apiKeyInput { color: #E2E8F0; border-color: #3A3A52; }
QPushButton#examPickAudioBtn { color: #94A3B8; }
QPushButton#examAddPickAudioBtn { color: #94A3B8; }
QLineEdit#examTtsInput { color: #E2E8F0; }
QLineEdit#examSingleTtsInput { color: #E2E8F0; }
QStatusBar#statusBar { background-color: #2A2A3E; border-top: 1px solid #3A3A52; }
"""