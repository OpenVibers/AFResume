/**
 * Client-side themed resume PDF. The canonical PDF (public/<profile.resumePdf>) is built by
 * resume/build_resume.py and never changes based on who's looking at it — it's the one a
 * recruiter or an ATS gets. This one is a bonus: generated in the visitor's own browser, in
 * whatever accent color they picked (or the site's default blue if they never opened the
 * picker), from the same JSON the page already renders from (#resume-data). Nothing here is
 * canonical content — it's a themed mirror of it.
 */
(function () {
  'use strict';
  var JSPDF_SRC = '/assets/vendor/jspdf/jspdf.umd.min.js';
  var btn = document.getElementById('themed-pdf-btn');
  if (!btn) return;

  function loadJsPdf() {
    if (window.jspdf && window.jspdf.jsPDF) return Promise.resolve();
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = JSPDF_SRC;
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error('jsPDF failed to load')); };
      document.head.appendChild(s);
    });
  }

  // jsPDF's built-in Helvetica is WinAnsi-encoded (Latin-1 extended): em/en dashes and the
  // middle dot render fine, but an arrow has no slot in that table and comes out as garbage.
  // Recursively clean every string in the parsed data once, rather than remembering to sanitize
  // every doc.text() call site.
  function sanitize(x) {
    if (typeof x === 'string') return x.replace(/→/g, '->');
    if (Array.isArray(x)) return x.map(sanitize);
    if (x && typeof x === 'object') {
      var out = {};
      for (var k in x) if (Object.prototype.hasOwnProperty.call(x, k)) out[k] = sanitize(x[k]);
      return out;
    }
    return x;
  }

  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }

  function buildPdf(data) {
    var jsPDF = window.jspdf.jsPDF;
    var doc = new jsPDF({ unit: 'pt', format: 'letter' });
    var PAGE_W = 612, PAGE_H = 792, MARGIN = 40, CONTENT_W = PAGE_W - MARGIN * 2;

    var accent = cssVar('--accent', '#4f7cff');
    var violet = cssVar('--violet', '#8b5cf6');
    var ember = cssVar('--accent-2', '#ff6a3d');
    var mint = cssVar('--accent-3', '#3ee6b0');
    var ink = '#12141c', muted = '#5a6072', paper = '#f6f7fb';

    var y = MARGIN;

    function ensureRoom(h) {
      if (y + h > PAGE_H - MARGIN) { doc.addPage(); paintPageBg(); y = MARGIN; }
    }
    function paintPageBg() {
      doc.setFillColor(paper);
      doc.rect(0, 0, PAGE_W, PAGE_H, 'F');
    }
    function sectionHeader(text, color) {
      ensureRoom(26);
      doc.setFillColor(color);
      doc.roundedRect(MARGIN, y, CONTENT_W, 20, 10, 10, 'F');
      doc.setTextColor('#ffffff');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10.5);
      doc.text(text.toUpperCase(), MARGIN + 12, y + 14);
      y += 32;
    }
    function bullets(list, indent) {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9.3);
      doc.setTextColor(ink);
      (list || []).forEach(function (b) {
        var lines = doc.splitTextToSize('•  ' + b, CONTENT_W - indent);
        ensureRoom(lines.length * 12 + 2);
        doc.text(lines, MARGIN + indent, y);
        y += lines.length * 12 + 2;
      });
    }

    paintPageBg();

    // ---- Header banner ----------------------------------------------------------------
    var bannerH = 92;
    doc.setFillColor(accent);
    doc.roundedRect(MARGIN, y, CONTENT_W, bannerH, 14, 14, 'F');
    doc.setTextColor('#ffffff');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(24);
    doc.text(data.profile.name, MARGIN + 20, y + 34);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10.5);
    var tagLines = doc.splitTextToSize(data.profile.tagline, CONTENT_W - 220);
    doc.text(tagLines, MARGIN + 20, y + 52);
    var contact = [
      data.profile.emailDisplay || data.profile.email,
      data.profile.phoneDisplay || data.profile.phone,
      data.profile.siteDisplay,
      data.profile.locationShort,
    ].filter(Boolean);
    doc.setFontSize(9);
    contact.forEach(function (line, i) {
      doc.text(line, MARGIN + CONTENT_W - 170, y + 24 + i * 13);
    });
    y += bannerH + 18;

    // ---- Capability chips (profile.seeking) ---------------------------------------------
    var chipColors = [accent, violet, ember, mint];
    var cx = MARGIN;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.6);
    (data.profile.seeking || []).forEach(function (s, i) {
      var w = doc.getTextWidth(s.label) + 20;
      if (cx + w > MARGIN + CONTENT_W) { cx = MARGIN; y += 22; }
      var c = chipColors[i % chipColors.length];
      doc.setFillColor(c);
      doc.roundedRect(cx, y, w, 18, 9, 9, 'F');
      doc.setTextColor('#ffffff');
      doc.text(s.label, cx + 10, y + 12.5);
      cx += w + 8;
    });
    y += 34;

    // ---- Profile ---------------------------------------------------------------------
    sectionHeader('Profile', accent);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.6);
    doc.setTextColor(ink);
    var pitchLines = doc.splitTextToSize(data.profile.pitch, CONTENT_W);
    ensureRoom(pitchLines.length * 13);
    doc.text(pitchLines, MARGIN, y);
    y += pitchLines.length * 13 + 18;

    // ---- Experience --------------------------------------------------------------------
    sectionHeader('Experience', violet);
    (data.experience || []).forEach(function (role) {
      ensureRoom(30);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(11.5);
      doc.setTextColor(ink);
      doc.text(role.role, MARGIN, y);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(muted);
      var dates = (role.start || '') + ' – ' + (role.end || '');
      doc.text(dates, MARGIN + CONTENT_W - doc.getTextWidth(dates), y);
      y += 14;
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(9.5);
      doc.setTextColor(accent);
      var co = role.company + (role.location ? '  ·  ' + role.location : '');
      doc.text(co, MARGIN, y);
      y += 14;
      bullets(role.bullets, 4);
      if (role.stack && role.stack.length) {
        doc.setFont('helvetica', 'italic');
        doc.setFontSize(8);
        doc.setTextColor(muted);
        var stackLines = doc.splitTextToSize(role.stack.join('  ·  '), CONTENT_W - 4);
        ensureRoom(stackLines.length * 10 + 4);
        doc.text(stackLines, MARGIN + 4, y);
        y += stackLines.length * 10 + 4;
      }
      y += 8;
    });
    y += 6;

    // ---- Selected work -------------------------------------------------------------------
    sectionHeader('Selected work', ember);
    (data.projects || []).forEach(function (p) {
      ensureRoom(28);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(ink);
      doc.text(p.title, MARGIN, y);
      y += 12;
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8.8);
      doc.setTextColor(muted);
      var sLines = doc.splitTextToSize(p.summary, CONTENT_W);
      doc.text(sLines, MARGIN, y);
      y += sLines.length * 11;
      if (p.links && p.links.live) {
        doc.setTextColor(accent);
        doc.setFontSize(8.4);
        doc.textWithLink(p.links.live.replace(/^https?:\/\//, ''), MARGIN, y, { url: p.links.live });
        y += 12;
      }
      y += 6;
    });
    y += 6;

    // ---- Skills ----------------------------------------------------------------------
    sectionHeader('Skills', mint);
    (data.skills || []).forEach(function (g) {
      var items = (g.items || []).map(function (it) { return it.name; }).join('  ·  ');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8.4);
      doc.setTextColor(accent);
      ensureRoom(24);
      doc.text(g.group.toUpperCase(), MARGIN, y);
      y += 11;
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(ink);
      var gLines = doc.splitTextToSize(items, CONTENT_W);
      ensureRoom(gLines.length * 12);
      doc.text(gLines, MARGIN, y);
      y += gLines.length * 12 + 10;
    });

    // ---- Education ---------------------------------------------------------------------
    sectionHeader('Education & links', accent);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9.2);
    doc.setTextColor(ink);
    var eduLines = doc.splitTextToSize(data.profile.education || '', CONTENT_W);
    ensureRoom(eduLines.length * 12);
    doc.text(eduLines, MARGIN, y);
    y += eduLines.length * 12 + 10;
    doc.setTextColor(accent);
    doc.setFontSize(9);
    doc.textWithLink(data.profile.siteDisplay, MARGIN, y, { url: data.profile.site });
    doc.textWithLink(data.profile.githubDisplay, MARGIN + 130, y, { url: data.profile.github });
    doc.textWithLink(data.profile.linkedinDisplay, MARGIN + 290, y, { url: data.profile.linkedin });

    // Footer on every page.
    var pages = doc.internal.getNumberOfPages();
    for (var i = 1; i <= pages; i++) {
      doc.setPage(i);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.6);
      doc.setTextColor(muted);
      doc.text(data.profile.name + '  ·  themed PDF, generated in your browser', MARGIN, PAGE_H - 20);
      doc.text(String(i) + ' / ' + pages, PAGE_W - MARGIN - doc.getTextWidth(String(i) + ' / ' + pages), PAGE_H - 20);
    }

    var fname = (data.profile.name || 'resume').replace(/\s+/g, '_') + '_Resume_Themed.pdf';
    doc.save(fname);
  }

  btn.addEventListener('click', function () {
    var label = btn.querySelector('span');
    var original = label ? label.textContent : null;
    btn.disabled = true;
    if (label) label.textContent = 'Generating…';
    loadJsPdf()
      .then(function () {
        var raw = document.getElementById('resume-data');
        var data = sanitize(JSON.parse(raw.textContent));
        buildPdf(data);
      })
      .catch(function (err) {
        console.warn('[resume-pdf] themed export failed:', err && err.message);
        if (label) label.textContent = "Couldn't generate — try Download PDF";
        setTimeout(function () { if (label) label.textContent = original; }, 3000);
      })
      .finally(function () {
        btn.disabled = false;
        if (label && label.textContent === 'Generating…') label.textContent = original;
      });
  });
})();
