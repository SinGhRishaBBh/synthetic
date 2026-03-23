import plotly.graph_objects as go

def apply_luminal_theme(fig, height=380, title=None):
    """
    Applies the Luminal (Stitch) dark theme styling to a Plotly figure.
    """
    if fig is None:
        return None

    # Update template to a dark template layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(family="Inter, sans-serif", color="#a7abb2", size=11),
        hoverlabel=dict(
            bgcolor="#141a20",
            font_size=11,
            font_family="Inter, sans-serif",
            bordercolor="rgba(129, 236, 255, 0.2)"
        ),
        xaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.04)",
            zerolinecolor="rgba(255, 255, 255, 0.04)",
            linecolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#a7abb2", size=10),
        ),
        yaxis=dict(
            gridcolor="rgba(255, 255, 255, 0.04)",
            zerolinecolor="rgba(255, 255, 255, 0.04)",
            linecolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#a7abb2", size=10),
        ),
    )

    if title:
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(family="Manrope, sans-serif", color="#fff", size=14, weight="bold"),
                x=0,
                xanchor='left'
            )
        )
    elif hasattr(fig, 'layout') and fig.layout.title.text:
         # Restyle existing title
         orig_title = fig.layout.title.text
         fig.update_layout(
            title=dict(
                text=orig_title,
                font=dict(family="Manrope, sans-serif", color="#fff", size=14, weight="bold"),
                x=0,
                xanchor='left'
            )
        )

    # Re-style markers/colors if they are default
    # For bar and histogram, we generally want primary glows if single trace
    if len(fig.data) == 1:
        if hasattr(fig.data[0], 'marker'):
             # If using continuous color scale like OrRd, maybe leave it, 
             # but standard bars should be primary
             pass

    return fig

def update_color_scale(fig, continuous_scale="ice"):
    """
    Updates continuous color scale if needed.
    """
    if not fig or not fig.data:
        return fig
        
    for trace in fig.data:
        if hasattr(trace, 'colorcontinuousscale'):
            # Re-scale to match glowing neon
            pass
            
    return fig
