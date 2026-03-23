import streamlit as st
import textwrap

def metric_card(title: str, value: str, subtitle: str, icon: str, growth: str = None, color: str = "primary"):
    """
    Renders a metric card matching the Stitch template design.
    """
    colors = {
        "primary": "text-[#81ecff] bg-[#81ecff]/10",
        "tertiary": "text-[#a98bff] bg-[#a98bff]/10",
        "error": "text-[#ff716c] bg-[#ff716c]/10",
    }
    
    icon_color_class = colors.get(color, "text-[#81ecff] bg-[#81ecff]/10")
    text_color_class = "text-[#81ecff]" if color == "primary" else "text-white"
    
    growth_html = f'<span class="text-sm font-bold {text_color_class} ml-2">{growth}</span>' if growth else ""
    
    html = f"""
    <div class="p-6 rounded-2xl glass-panel glow-border flex flex-col justify-between group transition-all duration-500 hover:-translate-y-1 h-full">
        <div class="flex justify-between items-center mb-6">
            <span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#a7abb2]/70 font-label">{title}</span>
            <div class="w-9 h-9 rounded-xl flex items-center justify-center {icon_color_class} group-hover:shadow-[0_0_15px_rgba(129,236,255,0.2)] transition-all">
                <span class="material-symbols-outlined text-lg" style="font-variation-settings: 'FILL' 0;">{icon}</span>
            </div>
        </div>
        <div>
            <div class="flex items-baseline gap-1">
                <span class="text-3xl font-extrabold text-white tracking-tight font-headline">{value}</span>
                {growth_html}
            </div>
            <p class="text-[10px] text-[#a7abb2] mt-1 font-medium font-body">{subtitle}</p>
        </div>
    </div>
    """
    st.markdown(html.replace('\n', ' '), unsafe_allow_html=True)

def glass_card_container(title: str, icon: str = None, description: str = None):
    """
    Returns a section inside a glass card container matching Stitch template rules.
    This just returns the opening HTML, so you can place items inside it.
    Can be used with st.container and custom CSS, or just fully custom HTML.
    
    To make it easier, we will create a function that returns a context manager or HTML content.
    For Streamlit layout inside columns, we might just want component containers.
    """
    icon_html = f'<span class="material-symbols-outlined text-lg text-[#81ecff]" style="font-variation-settings: \'FILL\' 0;">{icon}</span>' if icon else ""
    desc_html = f'<p class="text-xs text-[#a7abb2] opacity-80 mt-1 font-body">{description}</p>' if description else ""
    
    html = f"""
    <div class="glass-panel rounded-xl p-6 hover:translate-y-[-2px] transition-all duration-300 group border border-[#81ecff]/5 bg-[#141a20]/40 space-y-4">
        <div class="flex justify-between items-start">
            <div>
                <h4 class="text-base font-headline font-bold text-white">{title}</h4>
                {desc_html}
            </div>
            {icon_html}
        </div>
        <div class="pt-2">
    """
    return html.replace('\n', ' ')

def close_glass_card():
    return "</div></div>"

def section_header(title: str, subtitle: str = None):
    """
    Renders a header matching the Stitch layout.
    """
    sub_html = f'<p class="text-[#a7abb2] font-body text-sm mt-1 max-w-2xl">{subtitle}</p>' if subtitle else ""
    html = f"""
    <div class="mb-8">
        <h2 class="text-2xl font-extrabold font-headline tracking-tight text-white mb-1">{title}</h2>
        {sub_html}
    </div>
    """
    st.markdown(html.replace('\n', ' '), unsafe_allow_html=True)

def info_tooltip(text: str):
    """
    Renders an info tooltip icon with text.
    """
    html = f"""
    <div class="absolute right-4 top-4 group/tip">
        <span class="material-symbols-outlined text-sm text-[#a7abb2]/40 hover:text-[#81ecff] cursor-help">info</span>
        <div class="absolute right-0 top-6 w-48 p-2 rounded-lg bg-[#1a2027] border border-[#81ecff]/10 shadow-xl opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all text-[10px] text-[#eaeef6] z-20 backdrop-blur-md">
            {text}
        </div>
    </div>
    """
    return html.replace('\n', ' ')

def list_item_card(title: str, subtitle: str, icon: str, status_text: str = None, status_color: str = "primary"):
    """
    Renders a list item style card (like job queue).
    """
    status_html = ""
    if status_text:
        colors = {
            "primary": "bg-[#81ecff]/10 text-[#81ecff] border-[#81ecff]/20",
            "error": "bg-[#ff716c]/10 text-[#ff716c] border-[#ff716c]/20",
            "warning": "bg-[#ffb948]/10 text-[#ffb948] border-[#ffb948]/20",
        }
        color_class = colors.get(status_color, colors["primary"])
        status_html = f'<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border {color_class} text-[9px] font-black uppercase tracking-wider">{status_text}</span>'
        
    html = f"""
    <div class="flex items-center justify-between p-4 bg-[#141a20]/30 hover:bg-[#141a20]/60 rounded-xl border border-white/5 transition-colors group">
        <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-[#eaeef6] group-hover:text-[#81ecff] transition-colors">
                <span class="material-symbols-outlined text-lg">{icon}</span>
            </div>
            <div>
                <p class="text-sm font-bold text-white group-hover:text-[#81ecff] transition-colors">{title}</p>
                <p class="text-[10px] text-[#a7abb2] uppercase tracking-wide font-medium">{subtitle}</p>
            </div>
        </div>
        {status_html}
    </div>
    """
    st.markdown(html.replace('\n', ' '), unsafe_allow_html=True)
