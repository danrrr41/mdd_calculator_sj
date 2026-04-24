import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
import matplotlib
import math
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import sys
import ctypes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 고해상도 DPI 설정
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Matplotlib 한글 폰트 설정
matplotlib.use('TkAgg')
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False


class MDDApp:
    def __init__(self, root):
        self.root = root
        self.root.title('MDD Calculator')
        self.root.state('zoomed')
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 엔터 키 바인딩
        self.root.bind('<Return>', lambda event: self.update_plot())

        # 관심 종목 리스트
        self.favorites = ['QQQ', 'SPY', 'GOOG', 'NVDA', 'AAPL', 'MSFT', 'TSLA', 'AMD', 'PLTR', 'META', 'AMZN', 'MU']

        # 상단 입력 프레임
        input_frame = ttk.Frame(self.root, padding="3")
        input_frame.pack(side=tk.TOP, fill=tk.X)

        # 종목 코드 입력 (Combobox)
        ttk.Label(input_frame, text='종목 코드:').pack(side=tk.LEFT, padx=5)
        self.code_entry = ttk.Combobox(input_frame, width=10, values=self.favorites)
        self.code_entry.insert(0, 'NFLX')
        self.code_entry.pack(side=tk.LEFT, padx=2)
        self.code_entry.bind('<<ComboboxSelected>>', lambda event: self.update_plot())

        # 시작일 입력
        ttk.Label(input_frame, text='시작일:').pack(side=tk.LEFT, padx=5)
        self.start_entry = ttk.Entry(input_frame, width=10)
        self.start_entry.insert(0, '2004-01-01')
        self.start_entry.pack(side=tk.LEFT, padx=2)

        # 종료일 입력
        ttk.Label(input_frame, text='종료일:').pack(side=tk.LEFT, padx=5)
        self.end_entry = ttk.Entry(input_frame, width=10)
        self.end_entry.insert(0, '2026-01-30')
        self.end_entry.pack(side=tk.LEFT, padx=2)

        # 현재 날짜 사용 체크박스
        self.use_now_var = tk.BooleanVar(value=True)
        self.now_check = ttk.Checkbutton(input_frame, text='현재 날짜 사용', variable=self.use_now_var)
        self.now_check.pack(side=tk.LEFT, padx=5)

        # 회복률 기준 입력
        ttk.Label(input_frame, text='회복률 기준(%):').pack(side=tk.LEFT, padx=5)
        self.threshold_entry = ttk.Entry(input_frame, width=5)
        self.threshold_entry.insert(0, '80')
        self.threshold_entry.pack(side=tk.LEFT, padx=2)

        # 적용 버튼
        self.apply_btn = ttk.Button(input_frame, text='적용', command=self.update_plot)
        self.apply_btn.pack(side=tk.LEFT, padx=15)

        # 차트 영역 설정
        self.fig = plt.figure(figsize=(15, 7.5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 초기 실행
        self.root.after(100, self.update_plot)

    def on_closing(self):
        plt.close('all')
        self.root.destroy()
        sys.exit()

    def update_plot(self):
        self.apply_btn.config(text='적용 중...', state=tk.DISABLED)
        self.root.update_idletasks()

        try:
            target_code = self.code_entry.get().upper().strip()
            if target_code.isdigit():
                target_code += '.KS'

            start = self.start_entry.get()
            use_now = self.use_now_var.get()
            actual_end = datetime.now().strftime('%Y-%m-%d') if use_now else self.end_entry.get()

            label_text, price_label = ('현재', '현재가') if use_now else ('종료', '종료가')
            threshold_pct = float(self.threshold_entry.get())

            # 데이터 다운로드
            df = yf.download(target_code, start=start, end=actual_end, progress=False)
            if df.empty:
                raise ValueError('데이터 없음')

            # MultiIndex 처리 (yfinance 최신 버전 대응)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            price_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
            df = df[[price_col]].copy()
            df.columns = ['Price']

            # MDD 계산
            df['Peak'] = df['Price'].cummax()
            df['Drawdown'] = (df['Price'] - df['Peak']) / df['Peak'] * 100

            max_mdd_val = df['Drawdown'].min()
            max_mdd_date = df['Drawdown'].idxmin()

            last_price = df['Price'].iloc[-1]
            last_val = df['Drawdown'].iloc[-1]
            last_date = df.index[-1]
            current_peak = df['Peak'].iloc[-1]
            total_days = len(df)

            # 기준 가격 계산
            threshold_val = np.percentile(df['Drawdown'], 100 - threshold_pct)
            price_at_threshold = current_peak * (1 + threshold_val / 100)

            # 그래프 그리기
            self.fig.clear()
            gs = self.fig.add_gridspec(1, 2, width_ratios=[3, 1.1], left=0.05, right=0.98, top=0.9, bottom=0.1,
                                       wspace=0.1)
            ax_chart = self.fig.add_subplot(gs[0])
            ax_table = self.fig.add_subplot(gs[1])

            # MDD 차트
            ax_chart.plot(df.index, df['Drawdown'], color='red', linewidth=0.5, alpha=0.7)
            ax_chart.axhline(threshold_val, color='black', linestyle='--', linewidth=1, alpha=0.8)
            ax_chart.text(df.index[0], threshold_val + 0.5, f'  기준점 {threshold_val:.1f}%', color='black', fontsize=9,
                          fontweight='bold', va='bottom')

            # 주요 포인트 마킹
            ax_chart.scatter([max_mdd_date, last_date], [max_mdd_val, last_val], color=['darkred', 'blue'], s=35,
                             zorder=10, clip_on=False)

            ax_chart.annotate(f'MDD: {max_mdd_val:.1f}%\n({max_mdd_date.strftime("%Y-%m-%d")})',
                              xy=(max_mdd_date, max_mdd_val), xytext=(5, 5), textcoords='offset points',
                              ha='left', va='bottom', fontsize=10, fontweight='bold', color='darkred',
                              annotation_clip=False)

            ax_chart.annotate(f'{label_text}: {last_val:.1f}%\n({last_date.strftime("%Y-%m-%d")})',
                              xy=(last_date, last_val), xytext=(-5, 5), textcoords='offset points',
                              ha='right', va='bottom', fontsize=10, fontweight='bold', color='blue',
                              annotation_clip=False)

            # 정보 텍스트
            info_text = f"종목: {target_code}  |  기간: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}"
            info_text += f"\n최고가: {current_peak:.2f}  |  {price_label}: {last_price:.2f}  |  MDD: {max_mdd_val:.2f}%  |  기준가: {price_at_threshold:.2f}"
            ax_chart.text(0.5, 1.03, info_text, transform=ax_chart.transAxes, ha='center', va='bottom', fontsize=11,
                          color='black', fontweight='bold', linespacing=1.6)

            # X축 설정 (연도별 틱)
            year_ticks = pd.date_range(start=df.index[0], end=df.index[-1], freq='YS').tolist()
            final_ticks = [df.index[0]] + year_ticks + [df.index[-1]]
            ax_chart.set_xticks(final_ticks)
            ax_chart.xaxis.set_major_formatter(mdates.DateFormatter('%y.%m'))

            # Y축 설정
            ax_chart.set_ylim(math.floor(max_mdd_val / 10) * 10, 0)
            ax_chart.yaxis.set_major_formatter(mticker.PercentFormatter(100, decimals=0, symbol='%'))
            ax_chart.grid(True, which='both', color='lightgray', linestyle='--', linewidth=0.5, alpha=0.5)
            ax_chart.fill_between(df.index, df['Drawdown'], 0, color='red', alpha=0.05)
            plt.setp(ax_chart.get_xticklabels(), rotation=45, fontsize=9)

            # 테이블 데이터 계산
            thresholds = range(0, -105, -5)
            table_data, rec_vals, weight_vals = [], [], []
            for ts in thresholds:
                r_rate = len(df[df['Drawdown'] >= ts]) / total_days * 100
                if ts == 0:
                    w_days = len(df[df['Drawdown'] == 0])
                else:
                    w_days = len(df[(df['Drawdown'] >= ts) & (df['Drawdown'] < ts + 5)])
                weight = w_days / total_days * 100

                table_data.append([f"{ts}%", f"{r_rate:.1f}%", f"{weight:.1f}%"])
                rec_vals.append(r_rate)
                weight_vals.append(weight)

            # 컬러맵 적용
            cmap_rec = mcolors.LinearSegmentedColormap.from_list('rec', ['#ffffff', '#fff2cc'])
            cmap_weight = mcolors.LinearSegmentedColormap.from_list('weight', ['#ffffff', '#f4b183'])
            max_w = max(weight_vals) if weight_vals else 1

            cell_colors = []
            for r, w in zip(rec_vals, weight_vals):
                cell_colors.append(['white', cmap_rec(r / 100), cmap_weight(w / max_w)])

            ax_table.axis('off')
            the_table = ax_table.table(cellText=table_data, colLabels=['기준(MDD)', '회복률', '비중'],
                                       loc='center', cellLoc='center', cellColours=cell_colors,
                                       colColours=['#e0e0e0'] * 3)
            the_table.auto_set_font_size(False)
            the_table.set_fontsize(10)
            the_table.scale(1, 1.8)
            for (r, c), cell in the_table.get_celld().items():
                if r == 0: cell.set_text_props(fontweight='bold')

            self.canvas.draw()

        except Exception as e:
            print(f"Error: {e}")

        self.apply_btn.config(text='적용', state=tk.NORMAL)


if __name__ == '__main__':
    root = tk.Tk()
    app = MDDApp(root)
    root.mainloop()