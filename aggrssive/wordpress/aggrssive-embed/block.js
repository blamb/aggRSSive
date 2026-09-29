/* aggRSSive Embed block. Plain JS on the WordPress globals, so no build step is needed. */
(function (wp) {
  var el = wp.element.createElement;
  var __ = wp.i18n.__;
  var InspectorControls = wp.blockEditor.InspectorControls;
  var ServerSideRender = wp.serverSideRender;
  var C = wp.components;

  wp.blocks.registerBlockType('aggrssive/embed', {
    title: 'aggRSSive',
    description: __('A live, filtered feed bundle from your aggRSSive site.', 'aggrssive-embed'),
    icon: 'rss',
    category: 'embed',
    keywords: ['rss', 'feed', 'aggrssive'],
    supports: { html: false },
    edit: function (props) {
      var a = props.attributes, set = props.setAttributes;
      var site = a.site || (window.aggrssiveEmbed && window.aggrssiveEmbed.site) || '';
      var controls = el(InspectorControls, {},
        el(C.PanelBody, { title: __('aggRSSive', 'aggrssive-embed'), initialOpen: true },
          el(C.TextControl, { label: __('aggRSSive code', 'aggrssive-embed'), help: __('The part after /bundles/ in its address.', 'aggrssive-embed'), value: a.slug, onChange: function (v) { set({ slug: v }); } }),
          el(C.TextControl, { label: __('Site (leave blank for the default)', 'aggrssive-embed'), value: a.site, placeholder: window.aggrssiveEmbed ? window.aggrssiveEmbed.site : '', onChange: function (v) { set({ site: v }); } }),
          el(C.RangeControl, { label: __('Items', 'aggrssive-embed'), value: a.n, min: 1, max: 50, onChange: function (v) { set({ n: v }); } }),
          el(C.SelectControl, { label: __('Descriptions', 'aggrssive-embed'), value: a.desc, options: [{ label: 'Short excerpt', value: 'excerpt' }, { label: 'Full', value: 'full' }, { label: 'None', value: 'none' }], onChange: function (v) { set({ desc: v }); } }),
          el(C.ToggleControl, { label: __('Images', 'aggrssive-embed'), checked: a.img, onChange: function (v) { set({ img: v }); } }),
          el(C.ToggleControl, { label: __('Source names', 'aggrssive-embed'), checked: a.src, onChange: function (v) { set({ src: v }); } }),
          el(C.ToggleControl, { label: __('Dates', 'aggrssive-embed'), checked: a.date, onChange: function (v) { set({ date: v }); } }),
          el(C.SelectControl, { label: __('Theme', 'aggrssive-embed'), value: a.theme, options: [{ label: 'Light', value: 'light' }, { label: 'Dark', value: 'dark' }, { label: 'Match visitor', value: 'auto' }], onChange: function (v) { set({ theme: v }); } }),
          el(C.SelectControl, { label: __('Method', 'aggrssive-embed'), help: __('Script renders inline and matches your theme; iframe works where scripts are stripped.', 'aggrssive-embed'), value: a.mode, options: [{ label: 'Script', value: 'script' }, { label: 'Iframe', value: 'iframe' }], onChange: function (v) { set({ mode: v }); } }),
          a.mode === 'iframe' ? el(C.RangeControl, { label: __('Height (px)', 'aggrssive-embed'), value: a.height, min: 120, max: 2000, step: 10, onChange: function (v) { set({ height: v }); } }) : null
        )
      );
      var preview;
      if (!a.slug || !site) {
        preview = el(C.Placeholder, { icon: 'rss', label: 'aggRSSive', instructions: __('Enter the aggRSSive code in the block settings. Set the site address once under Settings → aggRSSive.', 'aggrssive-embed') });
      } else {
        // The script version can't run inside the editor, so preview with the iframe rendering in both modes.
        var q = '?n=' + a.n + '&desc=' + (a.desc === 'none' ? 0 : 1) + '&img=' + (a.img ? 1 : 0) + '&src=' + (a.src ? 1 : 0) + '&date=' + (a.date ? 1 : 0) + '&theme=' + a.theme;
        preview = el('iframe', { src: site.replace(/\/$/, '') + '/embed/' + a.slug + '/frame' + q, style: { width: '100%', height: (a.mode === 'iframe' ? a.height : 400) + 'px', border: '1px dashed #ccc', pointerEvents: 'none' }, title: 'aggRSSive preview' });
      }
      return el(wp.element.Fragment, {}, controls, el('div', wp.blockEditor.useBlockProps ? wp.blockEditor.useBlockProps() : {}, preview));
    },
    save: function () { return null; } // rendered by PHP
  });
})(window.wp);
