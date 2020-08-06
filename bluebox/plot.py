import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors
import pandas as pd


class Style:
    def __init__(self, attr, default=None, split=False, **rules):
        self.attr = attr
        self.default = default
        self.split = split
        self.rules = rules

    def __call__(self, item):
        attrs = getattr(item, self.attr).split('+')
        if self.split and len(attrs) > 1:
            return [self.rules.get(attr, self.default) for attr in attrs]
        else:
            # Use A when A+B+... specified but split is False.
            return self.rules.get(attrs[0], self.default)

    @classmethod
    def use(cls, style):
        return (lambda item: style(item)) if isinstance(style, cls) else (lambda item: style)


def plotGradient(ax, xy, width, height, color='r', cmap=None, gradient=lambda x, y: x, alpha=lambda x,y: x ** 2):
    # Convert the plot dimensions from data coords to pixels.
    xy = np.asarray(xy)
    bl, tr = ax.transData.transform((xy, xy + np.asarray((width, height))))
    bl, tr = np.round((bl, tr)).astype(int)
    w, h = np.abs(tr - bl)
    x, y = np.meshgrid(np.linspace(0, 1, w), np.linspace(0, 1, h), sparse=True, copy=False)
    # Initialize an RGBA image with these dimensions.
    img = np.empty((h, w, 4))
    # Fill with the requested gradient or color.
    if cmap is not None and gradient is not None:
        cmap = plt.get_cmap(cmap)
        z = gradient(x, y)
        img[:] = cmap(z)
    else:
        img[:] = matplotlib.colors.to_rgba(color)
    # Apply transparency if requested.
    if alpha is not None:
        img[:, :, 3] *= alpha(x, y)
    # Render the image at data coords aligned to display pixels.
    bl, tr = ax.transData.inverted().transform((bl, tr))
    ax.imshow(img, extent=(bl[0], tr[0], bl[1], tr[1]), aspect='auto')


def timeline(*items, start=2018.8, stop=2032.5, now=2020 + 8/12,
             width=14, item_height=0.25, item_space=0.05, year_pad=0.2, dpi=72,
             fillcolor='steelblue', edgecolor='k', edgestyle='-', alpha=1,
             textcolor='black', textsize=12, textweight='bold',
             save=None):
    """Plot a timeline chart.

    Parameters
    ----------
    start : float
        Left edge of chart in decimal years.
    stop : float
        Right edge of chart in decimal years.
    now : float or None
        Draw a dashed vertical line at the specified decimal year,  or omit if None.
    width : float
        Width of chart in inches. The corresponding pixel value is determined by dpi.
    item_height : float
        Height of each item in inches. The corresponding pixel value is determined by dpi.
    item_space : float
        Vertical space betwen items in inches. The corresponding pixel value is determined by dpi.
    year_pad : float
        Top and bottom padding in inches where year labels are drawn. The corresponding pixel
        value is determined by dpi.
    dpi : float
        Pixels per inch.
    fillcolor : str or Style
        Matplotlib color used to fill each timeline box.
    edgecolor : str or Style
        Matplotlib color used to stroke the edge of each timeline box.
    edgestyle : str or Style
        Matplotlib linestyle used to stroke the edge of each timeline box.
    alpha : float or Style
        Alpha transparency value applied to the timeline box fill end edge.
    textcolor : str or Style
        Matplotlib color used for the label within each timeline box.
    textweight : str or Style
        Matplotlib text weight used for the label within each timeline box.
    save : str or None.
        Save to the specified file name when not None.
    """
    items = pd.concat(items)

    fillcolor = Style.use(fillcolor)
    edgecolor = Style.use(edgecolor)
    edgestyle = Style.use(edgestyle)
    textcolor = Style.use(textcolor)
    textsize = Style.use(textsize)
    textweight = Style.use(textweight)
    alpha = Style.use(alpha)

    rows = {}
    visible = []
    item_row =  {}
    for item in items.itertuples(index=False):
        if item.start + item.duration < start or item.start > stop:
            # Filter out items that are not visible.
            continue
        # Assign this visible item to a row.
        row_name = item.row or item.name
        row_index = rows.get(row_name, len(rows))
        rows[row_name] = row_index
        item_row[item.name] = row_index
        visible.append(item)
    nrows = len(rows)

    height = item_height * nrows + item_space * (nrows - 1) + 2 * year_pad
    fig = plt.figure(figsize=(width, height), dpi=dpi, frameon=False)
    ax = plt.axes((0, 0, 1, 1))
    ax.axis('off')
    ax.add_artist(plt.Rectangle((0, 0), 1, 1, fc='w', ec='None', transform=ax.transAxes, zorder=-20))
    ax.set_xlim(start, stop)
    renderer = fig.canvas.get_renderer()
    transf = ax.transData.inverted()

    dy = (0.5 * item_height + year_pad) / (item_height + item_space)
    h = 0.5 * item_height / (item_height + item_space)
    ax.set_ylim(nrows - 1 + dy, -dy)

    lo = int(np.ceil(start))
    hi = int(np.floor(stop))
    for yr in range(lo, hi + 1):
        plt.axvline(yr, ls=':', c='lightgray', zorder=-10)
        if yr < hi:
            ax.text(yr + 0.5, -dy, str(yr), ha='center', va='top', fontsize=12, color='gray')
            ax.text(yr + 0.5, nrows - 1  + dy, str(yr), ha='center', va='bottom', fontsize=12, color='gray')

    for item in visible:
        i = item_row[item.name]
        a = alpha(item)

        # Define a helper function to fill with a single color.
        def fillbox(ylo, height, fc):
            box = plt.Rectangle((item.start, ylo), item.duration, height, fc=fc, ec='none', alpha=a)
            ax.add_artist(box)
            if item.ramp_up:
                plotGradient(
                    ax, (item.start - item.ramp_up, ylo), item.ramp_up, height,
                    color=fc, alpha=lambda x,y: a * x)

        # Fill this box, possibly with stacked colors.
        fc = fillcolor(item)
        if isinstance(fc, str):
            # Draw a single filled box for this item
            fillbox(i - h, 2 * h, fc)
        else:
            # Draw stacked boxes for each fill color.
            nstack = len(fc)
            subh = 2 * h / nstack
            for j in range(nstack):
                fillbox(i - h + j * subh, subh, fc[j])

        # Draw box edge, if requested.
        ec = edgecolor(item)
        if ec.lower() is not 'none':
            box = plt.Rectangle((item.start, i - h), item.duration, 2 * h, fc='none', ec=ec, ls=edgestyle(item), alpha=a)
            ax.add_artist(box)

        # Draw the text for this item.
        T = ax.text(
            item.start + 0.5 * item.duration, i, item.name,
            color=textcolor(item), fontsize=textsize(item), alpha=a,
            ha='center', va='center', fontweight='bold')
        # Adjust the text position if it does not fit when centered.
        bbox = T.get_window_extent(renderer=renderer)
        bbox = bbox.transformed(transf)
        if bbox.x0 < start:
            # Reposition at left edge.
            T.set_ha('left')
            T.set_position((start, i))
        elif bbox.x1 > stop:
            T.set_ha('right')
            T.set_position((stop, i))

    if now is not None:
        ax.axvline(now, year_pad / height, 1 - year_pad / height, ls='--', alpha=0.5, lw=2, c='r')

    if save:
        plt.savefig(save, facecolor=fig.get_facecolor())
