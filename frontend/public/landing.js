/* ═══════════════════════════════════════════
   RealEnglish Landing Page Scripts
   - GSAP hero entrance + parallax
   - Lenis smooth scroll
   - Scroll Stack card effect
   - Auth modal logic
   ═══════════════════════════════════════════ */

/* ── GSAP Hero Entrance ── */
gsap.registerPlugin(ScrollTrigger);
var heroTL = gsap.timeline({ defaults: { ease: 'power2.out' } });
heroTL.from('.hero-badge', { opacity: 0, y: 20, duration: 0.5 })
  .from('.hero h1', { opacity: 0, y: 30, duration: 0.6 }, '-=0.2')
  .from('.hero p', { opacity: 0, y: 20, duration: 0.5 }, '-=0.3')
  .from('.hero-btns', { opacity: 0, y: 20, duration: 0.5 }, '-=0.3')
  .from('.hero-illustration', { opacity: 0, scale: 0.9, duration: 0.7 }, '-=0.4')
      .from('.hero-illustration-left', { opacity: 0, scale: 0.85, duration: 0.7 }, '-=0.5');

gsap.to('.hero-bg-deco.d1', {
  scrollTrigger: { trigger: '#hero', start: 'top top', end: 'bottom top', scrub: true },
  y: 120, ease: 'none'
});
gsap.to('.hero-bg-deco.d2', {
  scrollTrigger: { trigger: '#hero', start: 'top top', end: 'bottom top', scrub: true },
  y: -80, ease: 'none'
});

/* ── Decorative SVGs: entrance + fast multi-speed parallax ── */
var decoSpeeds = [180, -220, 140]; // different speed & direction per SVG
document.querySelectorAll('.deco-svg').forEach(function(el, i) {
  gsap.from(el, {
    opacity: 0, y: 30, duration: 0.8, delay: i * 0.15,
    scrollTrigger: { trigger: '.scroll-stack-wrapper', start: 'top 80%', once: true }
  });
  gsap.to(el, {
    y: decoSpeeds[i], x: i % 2 === 0 ? 30 : -30,
    ease: 'none',
    scrollTrigger: { trigger: '.scroll-stack-wrapper', start: 'top bottom', end: 'bottom top', scrub: 0.4 }
  });
});

/* ── Geometric decorations fade-in ── */
ScrollTrigger.batch(['.geo-vert', '.geo-dots', '.geo-dash'], {
  onEnter: function(b) { gsap.from(b, { opacity: 0, duration: 0.8, stagger: 0.06, ease: 'power2.out' }); },
  start: 'top 70%', once: true
});

/* ── Section header fade-in ── */
ScrollTrigger.batch('.section-header-wrap', {
  onEnter: function (b) { gsap.from(b, { opacity: 0, y: 30, duration: 0.7, ease: 'power2.out' }); },
  start: 'top 85%', once: true
});

/* ── Steps ── */
ScrollTrigger.batch('.step', {
  onEnter: function (b) { gsap.from(b, { opacity: 0, scale: 0.9, duration: 0.5, stagger: 0.1, ease: 'back.out(1.4)' }); },
  start: 'top 85%', once: true
});

/* ── Stats count-up ── */
ScrollTrigger.create({
  trigger: '#stats', start: 'top 85%', once: true,
  onEnter: function () {
    document.querySelectorAll('.stat-num').forEach(function (el) {
      var end = parseInt(el.dataset.end) || 0;
      gsap.to(el, { innerText: end, duration: 1.6, snap: { innerText: 1 }, ease: 'power2.out' });
    });
  }
});

/* ── CTA ── */
ScrollTrigger.batch('.cta-card', {
  onEnter: function (b) { gsap.from(b, { opacity: 0, y: 40, duration: 0.6, ease: 'power2.out' }); },
  start: 'top 88%', once: true
});

/* ═══════════════════════════════════════════
   SCROLL STACK
   Cards pin & stack as user scrolls.
   Each card hits a pin-point then stays fixed
   while subsequent cards slide up underneath.
   ═══════════════════════════════════════════ */
(function () {
  var cards = document.querySelectorAll('.stack-card');
  if (!cards.length) return;

  var endEl = document.querySelector('.scroll-stack-end');

  var itemDistance = 400;
  var itemScale = 0.03;
  var itemStackDistance = 30;
  var stackPosition = '20%';
  var scaleEndPosition = '15%';
  var baseScale = 0.9;
  var rotationAmount = 0;
  var blurAmount = 0.1;

  function parsePct(val, total) {
    if (typeof val === 'string' && val.indexOf('%') !== -1) {
      return (parseFloat(val) / 100) * total;
    }
    return parseFloat(val);
  }

  function calculateProgress(scrollTop, start, end) {
    if (scrollTop < start) return 0;
    if (scrollTop > end) return 1;
    return (scrollTop - start) / (end - start);
  }

  // Get document-relative top position (walk offsetParents)
  function getDocTop(el) {
    var top = 0;
    while (el) { top += el.offsetTop; el = el.offsetParent; }
    return top;
  }

  // Cache initial document positions (before any transforms)
  var cardTops = [];
  cards.forEach(function (card, i) {
    if (i < cards.length - 1) card.style.marginBottom = itemDistance + 'px';
    card.style.willChange = 'transform, filter';
    card.style.transformOrigin = 'top center';
    card.style.backfaceVisibility = 'hidden';
    cardTops.push(getDocTop(card));
  });
  var endTop = endEl ? getDocTop(endEl) : 0;

  // Recalculate on image load
  window.addEventListener('load', function () {
    cards.forEach(function (card, i) { cardTops[i] = getDocTop(card); });
    endTop = endEl ? getDocTop(endEl) : 0;
  });

  // Lenis wraps body for full-page smooth scroll
  var lenis = new Lenis({
    duration: 1.2,
    easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)); },
    smoothWheel: true,
    touchMultiplier: 2,
    lerp: 0.1
  });

  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  function updateCardTransforms() {
    var scrollTop = window.scrollY;
    var vh = window.innerHeight;
    var stackPx = parsePct(stackPosition, vh);
    var scaleEndPx = parsePct(scaleEndPosition, vh);
    var pinEnd = endTop - vh / 2;
    var topCardIndex = 0;

    // Find which card is at stack top
    for (var j = 0; j < cards.length; j++) {
      var jTriggerStart = cardTops[j] - stackPx - itemStackDistance * j;
      if (scrollTop >= jTriggerStart) topCardIndex = j;
    }

    cards.forEach(function (card, i) {
      var cardTop = cardTops[i];
      var triggerStart = cardTop - stackPx - itemStackDistance * i;
      var triggerEnd = cardTop - scaleEndPx;
      var pinStart = triggerStart;

      // Scale: 1 → targetScale as card moves through trigger zone
      var scaleProgress = calculateProgress(scrollTop, triggerStart, triggerEnd);
      var targetScale = baseScale + i * itemScale;
      var scale = 1 - scaleProgress * (1 - targetScale);

      // Rotation
      var rotation = rotationAmount ? i * rotationAmount * scaleProgress : 0;

      // Blur: cards behind the top one get blurred
      var blur = 0;
      if (blurAmount && i < topCardIndex) {
        blur = Math.max(0, (topCardIndex - i) * blurAmount);
      }

      // Translate: pin to viewport or release
      var translateY = 0;
      if (scrollTop >= pinStart && scrollTop <= pinEnd) {
        translateY = scrollTop - cardTop + stackPx + itemStackDistance * i;
      } else if (scrollTop > pinEnd) {
        translateY = pinEnd - cardTop + stackPx + itemStackDistance * i;
      }

      var transform = 'translate3d(0,' + parseFloat(translateY.toFixed(1)) + 'px,0) scale(' + parseFloat(scale.toFixed(3)) + ')';
      if (rotation) transform += ' rotate(' + rotation + 'deg)';
      card.style.transform = transform;
      card.style.filter = blur > 0 ? 'blur(' + blur + 'px)' : '';
    });
  }

  lenis.on('scroll', updateCardTransforms);
  setTimeout(updateCardTransforms, 100);
})();

/* ═══════════════════════════════════════════
   AUTH MODAL LOGIC
   ═══════════════════════════════════════════ */
window.API = '/api/v1';
window.selRole = 'student';
window.loginRole = 'student';

window.req = function (path, data) {
  return fetch(window.API + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(function (r) {
    return r.json().then(function (d) { d._ok = r.ok; return d; });
  });
};

window.selectRole = function (el) {
  window.selRole = el.dataset.role;
  document.querySelectorAll('#roleToggle .role-btn').forEach(function (b) { b.classList.remove('sel'); });
  el.classList.add('sel');
  var inviteGroup = document.getElementById('inviteGroup');
  if (inviteGroup) inviteGroup.style.display = window.selRole === 'student' ? '' : 'none';
};

window.selectLoginRole = function (el) {
  window.loginRole = el.dataset.role;
  document.querySelectorAll('#loginRoleToggle .role-btn').forEach(function (b) { b.classList.remove('sel'); });
  el.classList.add('sel');
};

window.openModal = function (type) {
  window.closeModals();
  var id = type === 'login' ? 'loginModal' : 'registerModal';
  document.getElementById(id).classList.add('open');
};

window.closeModals = function () {
  document.querySelectorAll('.modal-overlay').forEach(function (m) { m.classList.remove('open'); });
  document.querySelectorAll('.form-err').forEach(function (e) { e.style.display = 'none'; e.textContent = ''; });
};

window.switchModal = function (type) { window.closeModals(); window.openModal(type); };

window.handleRegister = function () {
  var err = document.getElementById('regErr'), btn = document.getElementById('regBtn');
  var username = document.getElementById('regUser').value.trim();
  var email = document.getElementById('regEmail').value.trim();
  var password = document.getElementById('regPw').value;
  var inviteCode = document.getElementById('regInvite').value.trim();
  err.style.display = 'none';
  if (!username || !email || !password) { err.textContent = '请填写所有字段'; err.style.display = 'block'; return; }
  if (username.length < 2 || username.length > 50) { err.textContent = '用户名2-50字符'; err.style.display = 'block'; return; }
  if (password.length < 8 || !/[a-zA-Z]/.test(password) || !/[0-9]/.test(password)) { err.textContent = '密码至少8位且含字母和数字'; err.style.display = 'block'; return; }
  btn.disabled = true; btn.textContent = '注册中...';
  var body = { username: username, email: email, password: password, role: window.selRole };
  if (inviteCode) body.invite_code = inviteCode.toUpperCase();
  window.req('/auth/register', body).then(function (res) {
    btn.disabled = false; btn.textContent = '注册';
    if (!res._ok) { err.textContent = res.detail || '注册失败'; err.style.display = 'block'; return; }
    window.onAuthSuccess(res.data);
  });
};

window.handleLogin = function () {
  var err = document.getElementById('loginErr'), btn = document.getElementById('loginBtn');
  var login = document.getElementById('loginId').value.trim();
  var password = document.getElementById('loginPw').value;
  err.style.display = 'none';
  if (!login || !password) { err.textContent = '请填写邮箱/用户名和密码'; err.style.display = 'block'; return; }
  btn.disabled = true; btn.textContent = '登录中...';
  window.req('/auth/login', { login: login, password: password, role: window.loginRole }).then(function (res) {
    btn.disabled = false; btn.textContent = '登录';
    if (!res._ok) { err.textContent = res.detail || '登录失败'; err.style.display = 'block'; return; }
    window.onAuthSuccess(res.data);
  });
};

window.onAuthSuccess = function (data) {
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('userInfo', JSON.stringify(data.user));
  if (data.user.level) localStorage.setItem('userLevel', data.user.level);
  window.closeModals();
  var dest = data.user.role === 'teacher' ? '/app.html#/teacher' : '/app.html#/student';
  window.location.href = dest;
};

window.checkAuth = function () {
  var token = localStorage.getItem('access_token');
  var userInfo = JSON.parse(localStorage.getItem('userInfo') || 'null');
  var nav = document.getElementById('navLinks');
  if (token && userInfo) {
    var label = userInfo.role === 'teacher' ? '教师端' : '学习中心';
    var dest = userInfo.role === 'teacher' ? '/app.html#/teacher' : '/app.html#/student';
    nav.innerHTML = '<span style="font-size:13px;color:var(--text2);margin-right:4px">' + (userInfo.username || '') + '</span><a href="' + dest + '" class="nav-btn nav-user">进入' + label + '</a><button class="nav-btn nav-login" onclick="window.logout()">退出</button>';
  } else {
    nav.innerHTML = '<button class="nav-btn nav-login" onclick="window.openModal(\'login\')">登录</button><button class="nav-btn nav-start" onclick="window.openModal(\'register\')">免费注册</button>';
  }
};

window.logout = function () {
  localStorage.removeItem('access_token');
  localStorage.removeItem('userInfo');
  localStorage.removeItem('userLevel');
  window.checkAuth();
};

window.scrollToSection = function (sel) {
  var el = document.querySelector(sel);
  if (el) el.scrollIntoView({ behavior: 'smooth' });
};

// Init
document.querySelectorAll('.modal-overlay').forEach(function (o) {
  o.addEventListener('click', function (e) { if (e.target === o) window.closeModals(); });
});
document.addEventListener('keydown', function (e) { if (e.key === 'Escape') window.closeModals(); });
window.checkAuth();
