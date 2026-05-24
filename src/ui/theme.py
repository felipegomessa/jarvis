"""Tema global da UI: cores, fonte Inter, locale Quasar PT-BR, CSS overrides.

Chame `apply_theme()` UMA vez por página (dentro de @ui.page) antes de renderizar
componentes. As chamadas globais (add_head_html, add_css, app.colors) são
idempotentes por sessão.
"""

from __future__ import annotations

from nicegui import app, ui

# Paleta — espelha a especificação visual ChatGPT-inspired
COLOR_BG = "#000000"
COLOR_SIDEBAR = "#050505"
COLOR_CARD_ACTIVE = "#2B2B2B"
COLOR_INPUT = "#2A2A2A"
COLOR_INPUT_BORDER = "#3A3A3A"
COLOR_TEXT_PRIMARY = "#F5F5F5"
COLOR_TEXT_SECONDARY = "#B8B8B8"
COLOR_BLUE_ACTION = "#0A84FF"
COLOR_GREEN_AVATAR = "#19C37D"

# Cores do calendário moram em src/ui/components/calendar_colors.py (single source).

_THEME_APPLIED = False


def apply_theme() -> None:
    """Aplica o tema dark ChatGPT-like + Inter font + locale Quasar PT-BR."""
    global _THEME_APPLIED

    # app.colors() pode ser chamada várias vezes — Quasar sobrescreve cada vez.
    # Mas evitamos add_head_html / add_css repetidos pra não duplicar.
    app.colors(
        primary=COLOR_BLUE_ACTION,
        secondary="#9c27b0",
        accent=COLOR_GREEN_AVATAR,
        dark=COLOR_BG,
        dark_page=COLOR_BG,
    )

    if _THEME_APPLIED:
        return
    _THEME_APPLIED = True

    # Inter font + Quasar locale PT-BR via <head>
    ui.add_head_html(
        """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script>
/* Aplica locale PT-BR no Quasar (calendários, datepickers, etc.) */
(function () {
    function applyLocale() {
        if (!window.Quasar || !window.Quasar.lang) {
            return setTimeout(applyLocale, 50);
        }
        try {
            window.Quasar.lang.set({
                isoName: 'pt-BR',
                nativeName: 'Português (Brasil)',
                label: {
                    clear: 'Limpar', ok: 'OK', cancel: 'Cancelar', close: 'Fechar',
                    set: 'Definir', select: 'Selecionar', reset: 'Redefinir',
                    remove: 'Remover', update: 'Atualizar', create: 'Criar',
                    search: 'Buscar', filter: 'Filtrar', refresh: 'Atualizar',
                    expand: 'Expandir', collapse: 'Recolher'
                },
                date: {
                    days: 'Domingo_Segunda_Terça_Quarta_Quinta_Sexta_Sábado'.split('_'),
                    daysShort: 'Dom_Seg_Ter_Qua_Qui_Sex_Sáb'.split('_'),
                    months: 'Janeiro_Fevereiro_Março_Abril_Maio_Junho_Julho_Agosto_Setembro_Outubro_Novembro_Dezembro'.split('_'),
                    monthsShort: 'Jan_Fev_Mar_Abr_Mai_Jun_Jul_Ago_Set_Out_Nov_Dez'.split('_'),
                    firstDayOfWeek: 0,
                    format24h: true,
                    pluralDay: 'dias'
                },
                table: { noData: 'Sem dados disponíveis', noResults: 'Nenhum resultado' }
            });
        } catch (e) { console.warn('Falha ao aplicar locale PT-BR:', e); }
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyLocale);
    } else {
        applyLocale();
    }
})();
</script>
""",
        shared=True,
    )

    # CSS overrides — preto absoluto, Inter, pill input, etc.
    ui.add_css(
        f"""
:root {{
    --jarvis-bg: {COLOR_BG};
    --jarvis-sidebar: {COLOR_SIDEBAR};
    --jarvis-text: {COLOR_TEXT_PRIMARY};
    --jarvis-text-2: {COLOR_TEXT_SECONDARY};
    --jarvis-border: #1f1f1f;
    --jarvis-blue: {COLOR_BLUE_ACTION};
    --jarvis-green: {COLOR_GREEN_AVATAR};
}}

body, .q-page-container, .q-page, .q-layout, .q-drawer {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI',
                 'Helvetica Neue', sans-serif !important;
    background-color: {COLOR_BG} !important;
    color: {COLOR_TEXT_PRIMARY};
}}
.q-drawer {{
    background-color: {COLOR_SIDEBAR} !important;
    border-right: 1px solid var(--jarvis-border) !important;
    transition: width 0.2s ease, min-width 0.2s ease, max-width 0.2s ease !important;
}}
/* Modo mini (sanfona): 60px com transição suave. Quasar adiciona a classe
   .q-drawer--mini ao DOM quando a prop `mini` é setada. */
.q-drawer--mini {{
    width: 60px !important;
    min-width: 60px !important;
    max-width: 60px !important;
}}
.q-drawer--mini .jarvis-recent {{ display: none !important; }}
/* Em modo expandido, jarvis-mini-only some; jarvis-full-only mostra. */
.jarvis-mini-only {{ display: none !important; }}
.jarvis-full-only {{ display: flex !important; }}
/* Em modo mini, inverte. */
.q-drawer--mini .jarvis-mini-only {{ display: flex !important; }}
.q-drawer--mini .jarvis-full-only {{ display: none !important; }}
.q-header {{ background: transparent !important; }}
/* Esconde indicadores default do NiceGUI/Quasar que podem aparecer no canto. */
.nicegui-content > .q-loading-bar,
.q-loading-bar,
.q-notification--top {{ z-index: 9999 !important; }}

/* Pill input do chat */
.jarvis-pill {{
    background-color: {COLOR_INPUT};
    border: 1px solid {COLOR_INPUT_BORDER};
    border-radius: 28px;
    padding: 6px 10px 6px 12px;
}}
.jarvis-pill .q-field {{ background: transparent; }}
.jarvis-pill .q-field__control,
.jarvis-pill .q-field__control:before,
.jarvis-pill .q-field__control:after {{
    background-color: transparent !important;
    border: none !important;
}}
.jarvis-pill input {{ color: {COLOR_TEXT_PRIMARY} !important; font-size: 15px; }}

/* Botão azul de envio (circular) */
.jarvis-send-btn .q-btn__content {{ color: white; }}

/* Recentes: ellipsis */
.jarvis-recent .q-item {{
    border-radius: 6px;
    padding: 6px 10px !important;
    min-height: 32px !important;
}}
.jarvis-recent .q-item:hover {{ background-color: #161616 !important; }}
.jarvis-recent .q-item__label {{
    font-size: 13px !important;
    color: #ddd !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
}}

/* Tool call card — discreto (legado, ainda em uso para outros componentes) */
.jarvis-tool-card {{
    background: #0d0d0d !important;
    border: 1px solid var(--jarvis-border) !important;
    border-radius: 10px;
    margin: 6px 0;
}}
.jarvis-tool-card .q-expansion-item__container {{ background: transparent; }}

/* Tool call chip — clicável (abre dialog modal com I/O). Visível em fundo preto */
.jarvis-tool-chip {{
    display: inline-flex !important;
    align-items: center;
    background: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 16px;
    padding: 4px 12px;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease;
    width: auto;
    flex: 0 0 auto;
}}
.jarvis-tool-chip:hover {{
    background: #2a2a2a;
    border-color: {COLOR_BLUE_ACTION};
}}

/* Avatar verde com iniciais */
.jarvis-avatar-user {{
    background-color: {COLOR_GREEN_AVATAR} !important;
    color: white !important;
    font-weight: 600;
}}

/* Chips do calendário */
.jarvis-cal-chip {{
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 4px;
    margin: 1px 0;
    cursor: pointer;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.jarvis-cal-chip.task-done {{
    text-decoration: line-through;
    opacity: 0.55;
}}

/* Célula do grid do mês */
.jarvis-cal-cell {{
    border-right: 1px solid var(--jarvis-border);
    border-bottom: 1px solid var(--jarvis-border);
    min-height: 110px;
    padding: 4px;
    cursor: pointer;
    transition: background 0.15s ease;
}}
.jarvis-cal-cell:hover {{ background-color: #0a0a0a; }}
.jarvis-cal-cell.other-month {{ background-color: #060606; }}
.jarvis-cal-cell.today-cell {{ background-color: #001829; }}

.jarvis-day-number {{
    font-size: 12px;
    color: #ccc;
    padding: 2px 4px;
}}
.jarvis-day-number.today {{
    background: {COLOR_BLUE_ACTION};
    color: white;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
}}
.jarvis-day-number.other-month {{ color: #444; }}

/* Headers do grid (DOM SEG ...) */
.jarvis-weekday-header {{
    font-size: 11px;
    color: #888;
    font-weight: 600;
    text-align: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--jarvis-border);
}}

/* Markdown render no chat */
.jarvis-md-chat code {{
    background: #1a1a1a;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.9em;
}}
.jarvis-md-chat pre {{
    background: #0a0a0a;
    border: 1px solid var(--jarvis-border);
    padding: 10px;
    border-radius: 6px;
    overflow-x: auto;
}}

/* Scrollbar discreta */
::-webkit-scrollbar {{ width: 8px; height: 8px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{ background: #2a2a2a; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: #3a3a3a; }}

/* Wizard cards (Evento vs Tarefa) */
.jarvis-wizard-card {{
    background: #0a0a0a;
    border: 1px solid var(--jarvis-border);
    border-radius: 12px;
    padding: 24px;
    cursor: pointer;
    transition: border-color 0.15s ease, transform 0.1s ease;
}}
.jarvis-wizard-card:hover {{
    border-color: {COLOR_BLUE_ACTION};
    transform: translateY(-2px);
}}

/* Dialog cards reutilizáveis (Materials, Calendar, Tasks, Audit) */
.jarvis-dialog-card {{
    background: var(--jarvis-bg) !important;
    color: var(--jarvis-text) !important;
    border: 1px solid var(--jarvis-border);
    border-radius: 14px;
    padding: 20px 24px;
}}
.jarvis-dialog-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--jarvis-border);
    margin-bottom: 16px;
}}
.jarvis-dialog-header__title {{
    font-size: 18px;
    font-weight: 600;
    color: var(--jarvis-text);
    display: flex;
    align-items: center;
    gap: 10px;
}}
.jarvis-dialog-subtitle {{
    color: var(--jarvis-text-2);
    font-size: 13px;
    margin-bottom: 12px;
}}
.jarvis-doc-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-radius: 8px;
    background: #0d0d0d;
    border: 1px solid transparent;
    transition: border-color 0.15s ease;
}}
.jarvis-doc-row:hover {{ border-color: var(--jarvis-border); }}
.jarvis-doc-row__title {{
    font-weight: 600;
    color: var(--jarvis-text);
}}
.jarvis-doc-row__meta {{
    color: var(--jarvis-text-2);
    font-size: 11px;
}}
.jarvis-doc-row__path {{
    color: #666;
    font-size: 11px;
    font-style: italic;
}}
.jarvis-upload-zone {{
    border: 1.5px dashed #2f2f2f;
    border-radius: 12px;
    background: #0a0a0a;
    padding: 16px;
    transition: border-color 0.15s ease, background 0.15s ease;
}}
.jarvis-upload-zone:hover {{
    border-color: {COLOR_BLUE_ACTION};
    background: #0d1419;
}}
""",
        shared=True,
    )


def reset_theme_for_tests() -> None:
    """Permite que testes re-apliquem o tema (limpa a flag)."""
    global _THEME_APPLIED
    _THEME_APPLIED = False
