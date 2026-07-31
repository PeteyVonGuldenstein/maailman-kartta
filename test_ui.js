// Käyttöliittymän savutesti oikealla selaimella (Chromium, headless).
// Täydentää test_game.js:ää, joka testaa vain puhtaat funktiot ilman DOM:ia:
// tässä ajetaan aito selain, joka paljastaa myös asettelu- ja ajastinbugit.
//
// Käyttö (aja make_offline.py ensin):
//   npx playwright install chromium     # kerran; binäärit ~/.cache/ms-playwright
//   node test_ui.js [polku.html]
//
// Tarkistaa: valikon tekstit molemmilla kielillä, sääntöluvut DIFFS- ja
// CHALLENGE-tauluista, minikartan kerrosten kohdistuksen, mittakaavajanan,
// merkkiin tarttumisen, laskeutumisen, lähtölaskurin, kellon, haasteen
// sekä sen ettei kesken lopetettu kierros jatku seuraavaan peliin.
const fs = require("fs");
const path = require("path");
const cp = require("child_process");

// playwright ja Chromium löytyvät myös npx-välimuistista, jos niitä ei ole
// asennettu projektiin
function findPlaywright() {
  try { return require("playwright"); } catch (e) {}
  const npx = path.join(process.env.HOME || "/root", ".npm/_npx");
  for (const d of fs.existsSync(npx) ? fs.readdirSync(npx) : []) {
    const p = path.join(npx, d, "node_modules/playwright");
    if (fs.existsSync(p)) return require(p);
  }
  throw new Error("playwright puuttuu: aja 'npx playwright install chromium'");
}
function findChrome() {
  if (process.env.CHROME) return process.env.CHROME;
  const out = cp.execSync(
    "ls -d ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell " +
    "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome 2>/dev/null | head -1",
    { shell: "/bin/bash" }).toString().trim();
  return out || undefined;   // undefined = playwrightin oma oletuspolku
}
const { chromium } = findPlaywright();

const FILE = "file://" + path.resolve(process.argv[2] ||
  path.join(__dirname, "maailman-kartta.html"));
const ok = [], fail = [];
const check = (cond, msg) => (cond ? ok : fail).push(msg);

(async () => {
  const browser = await chromium.launch({
    executablePath: findChrome(),
    args: ["--no-sandbox"],   // root-käyttäjä
  });
  const page = await browser.newPage({ viewport: { width: 420, height: 820 } });
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  page.on("console", m => m.type() === "error" && errors.push(m.text()));
  await page.goto(FILE);
  await page.waitForSelector("#contbtns button");

  // --- 3a: tekstit tulevat sanakirjasta ja luvut sääntötauluista
  check((await page.textContent("#title")).includes("MAAILMAN KARTTA"), "otsikko");
  const intro2 = await page.textContent("#intro2");
  check(/joka 10\..*joka 15\..*joka 20\./s.test(intro2), "intro2 luvut DIFFS-taulusta");
  check((await page.textContent("#ch-d")).includes("15 kohdetta") &&
        (await page.textContent("#ch-d")).includes("1:50"), "haasteen kuvaus CHALLENGE-taulusta");
  check((await page.textContent('button[data-mode="pk"]')).includes("Pääkaupungit"), "pelimuodon nimi");
  check(await page.isHidden("#jswarn"), "ei JS-varoitusta");
  // englanti ja paluu suomeen
  await page.click("#langbtn");
  check(/every 10th.*every 15th.*every 20th/s.test(await page.textContent("#intro2")), "intro2 englanniksi");
  check((await page.textContent("#ch-d")).includes("15 targets"), "haasteen kuvaus englanniksi");
  await page.click("#langbtn");
  check((await page.textContent("#intro1")).includes("Lennä helikopterilla"), "paluu suomeen");

  // --- 2b: minikartan kerrokset päällekkäin
  await page.click('#contbtns button[data-cont="suomi"]');
  if (!(await page.getAttribute("#learnbtn", "class") || "").includes("sel"))
    await page.click("#learnbtn");
  await page.click('button[data-mode="pk"]');
  await page.waitForFunction(() => document.querySelector("#task").textContent.includes("Etsi"));
  const box = await page.evaluate(() => {
    const a = document.getElementById("mini").getBoundingClientRect();
    const b = document.getElementById("miniov").getBoundingClientRect();
    const sb = document.getElementById("scalebar").getBoundingClientRect();
    return { a: [a.x, a.y, a.width, a.height], b: [b.x, b.y, b.width, b.height],
             sw: sb.width, scale: document.getElementById("scaletxt").textContent,
             vb: document.getElementById("miniov").getAttribute("viewBox"),
             view: document.getElementById("miniview").getAttribute("width") };
  });
  check(box.a.every((v, i) => Math.abs(v - box.b[i]) < 0.6),
    "minikartan kerrokset kohdakkain: " + JSON.stringify(box.a) + " vs " + JSON.stringify(box.b));
  check(box.a[2] > 90 && box.a[3] > 90, "minikartalla kokoa: " + box.a[2] + "x" + box.a[3]);
  check(Math.abs(box.sw - box.a[2]) < 0.6, "mittakaavajana minikartan levyinen");
  check(/^\d[\d\s]* km$/.test(box.scale), "mittakaavan lukema: " + box.scale);
  check(box.vb === "0 0 1000 1678", "merkkikerroksen viewBox: " + box.vb);
  check(+box.view > 0, "näkymäkehys piirretty");
  await page.screenshot({ path: path.join(process.env.TMPDIR || "/tmp", "kartta_ui.png") });

  // --- 2a: välimuistiin luettu merkkilista toimii yhä (kosketus tarttuu merkkiin)
  const snap = await page.evaluate(() => {
    const w = innerWidth, h = innerHeight;
    for (const d of document.querySelectorAll(".dot")) {
      const r = d.getBoundingClientRect();
      if (r.x > 170 && r.x < w - 120 && r.y > 120 && r.y < h - 220)
        return { sx: r.x + r.width / 2, sy: r.y + r.height / 2,
                 cx: +d.getAttribute("cx"), cy: +d.getAttribute("cy"),
                 name: d.dataset.name };
    }
    return null;
  });
  check(!!snap, "näkyvä kaupunkimerkki löytyi");
  if (snap) {
    await page.mouse.click(snap.sx + 12, snap.sy + 12);   // 12 px merkin vierestä; ilman tarttumista ero jäisi ~9 yksikköä
    await page.waitForTimeout(1500);
    const h = await page.evaluate(() => document.getElementById("heli")
      .getAttribute("transform").match(/translate\(([-\d.]+) ([-\d.]+)\)/).slice(1).map(Number));
    check(Math.hypot(h[0] - snap.cx, h[1] - snap.cy) < 3,
      `kosketus tarttui merkkiin ${snap.name}: ${h} vs ${[snap.cx, snap.cy]}`);
  }

  // --- 1a: lennä kohteeseen, laskeudu, lopeta juhlinnan aikana ja aloita heti uusi peli
  // Ohjaus nuolinäppäimillä kohti kohteen merkkiä, lopuksi laskeutuminen.
  async function flyAndLand(target) {
    const pos = () => page.evaluate(name => {
      const m = document.getElementById("heli").getAttribute("transform")
        .match(/translate\(([-\d.]+) ([-\d.]+)\)/);
      const d = document.querySelector(`.dot[data-name="${name}"]`);
      return { hx: +m[1], hy: +m[2], tx: +d.getAttribute("cx"), ty: +d.getAttribute("cy") };
    }, target);
    const held = new Set();
    for (let i = 0; i < 400; i++) {
      const p = await pos();
      const dx = p.tx - p.hx, dy = p.ty - p.hy;
      if (Math.hypot(dx, dy) < 6) break;
      const want = new Set();
      if (Math.abs(dx) > 3) want.add(dx > 0 ? "ArrowRight" : "ArrowLeft");
      if (Math.abs(dy) > 3) want.add(dy > 0 ? "ArrowDown" : "ArrowUp");
      for (const k of held) if (!want.has(k)) { await page.keyboard.up(k); held.delete(k); }
      for (const k of want) if (!held.has(k)) { await page.keyboard.down(k); held.add(k); }
      await page.waitForTimeout(20);
    }
    for (const k of held) await page.keyboard.up(k);
    await page.waitForTimeout(120);
    await page.keyboard.press("Space");
    await page.waitForTimeout(150);
    return page.textContent("#toast");
  }
  const target = await page.textContent("#task b");
  const toast = await flyAndLand(target);
  check(/Löytyi/.test(toast), "laskeutuminen kohteeseen onnistui (" + target + "): " + toast);

  // lopetus kesken löytöjuhlinnan (< 1,2 s) ja uusi peli heti perään
  await page.click("#quitbtn");
  check(await page.isVisible("#start"), "✕ palasi valikkoon");
  await page.click('button[data-mode="pk"]');
  await page.waitForFunction(() => document.querySelector("#task").textContent.includes("Etsi"));
  const first = await page.textContent("#task b");
  const stats1 = await page.textContent("#stats");
  await page.waitForTimeout(1600);   // vanha nextTask olisi lauennut tässä välissä
  const after = await page.textContent("#task b");
  const stats2 = await page.textContent("#stats");
  check(first === after, `uuden pelin kohde pysyi: ${first} → ${after}`);
  check(stats1 === stats2 && /^0\//.test(stats1), `laskuri pysyi nollassa: ${stats1} → ${stats2}`);
  check(!(await page.isVisible("#end")), "peli ei loppunut itsestään");

  // --- lähtölaskuri ja kello (clearPending ei saa rikkoa niitä)
  await page.click("#quitbtn");
  await page.click("#learnbtn");                       // opettelu pois
  await page.click('button[data-mode="pk"]');
  check(await page.isVisible("#count"), "lähtölaskuri näkyy");
  check((await page.textContent("#count")) === "5", "lähtölaskuri alkaa viidestä");
  await page.waitForSelector("#count", { state: "hidden", timeout: 8000 });
  const clock1 = await page.textContent("#stats");
  await page.waitForTimeout(1200);
  const clock2 = await page.textContent("#stats");
  check(/2:00|1:5\d/.test(clock1) && clock1 !== clock2, `kello käy: ${clock1} → ${clock2}`);

  // --- haaste (oma lähtölaskuri ja maanosan vaihto)
  await page.click("#quitbtn");
  await page.click("#challengebtn");
  check(await page.isVisible("#count"), "haasteen lähtölaskuri näkyy");
  check(/maanosa 1\/6/.test(await page.textContent("#toast")), "haaste kertoo maanosan: " +
    (await page.textContent("#toast")));
  await page.waitForSelector("#count", { state: "hidden", timeout: 8000 });
  check(/^0\/90 · 1:5\d/.test(await page.textContent("#stats")),
    "haasteen laskuri 0/90: " + (await page.textContent("#stats")));
  await page.click("#quitbtn");
  check(await page.isVisible("#start") && !(await page.isVisible("#count")),
    "haasteesta pääsi valikkoon");

  // --- maakunnat: kuntakeskukset pistekohteina kuntien rinnalla
  await page.click("#mktoggle");
  await page.click('#mkbtns button[data-cont="mk_uusimaa"]');
  check((await page.textContent("#lbl-pk")) === "Kuntakeskukset",
    "maakunnan pelimuoto: " + (await page.textContent("#lbl-pk")));
  check((await page.textContent("#lbl-maa")) === "Kunnat", "Kunnat-nappi ennallaan");
  check(await page.isVisible('button[data-mode="seka"]'), "Sekoitus näkyy maakunnalla");
  check(!(await page.isVisible('button[data-mode="kau"]')) &&
        !(await page.isVisible('button[data-mode="luonto"]')), "muut muodot piilossa");
  await page.click("#learnbtn");   // opettelu takaisin päälle
  // merkit näkyvät myös Kunnat-tilassa (suunnistusapuna)
  await page.click('button[data-mode="maa"]');
  await page.waitForFunction(() => document.querySelector("#task").textContent.includes("Etsi"));
  const dotsMaa = await page.evaluate(() => document.querySelectorAll(".dot").length);
  check(dotsMaa === 26, "Kunnat-tilassa Uudenmaan 26 keskusmerkkiä: " + dotsMaa);
  check((await page.textContent("#task")).startsWith("Etsi kunta:"), "HUD: Etsi kunta");
  // kuntakeskustila: oma HUD-teksti, merkit ja toimiva laskeutuminen
  await page.click("#quitbtn");
  await page.click('button[data-mode="pk"]');
  await page.waitForFunction(() => document.querySelector("#task").textContent.includes("Etsi"));
  check((await page.textContent("#task")).startsWith("Etsi kuntakeskus:"),
    "HUD: " + (await page.textContent("#task")));
  const kunta = await page.textContent("#task b");
  const kToast = await flyAndLand(kunta);
  check(/Löytyi/.test(kToast), `laskeutuminen kuntakeskukseen (${kunta}): ${kToast}`);
  check(await page.evaluate(n => !!document.querySelector(`.dot.found[data-name="${n}"]`), kunta),
    "löydetty kuntakeskus merkittiin vihreäksi");

  check(errors.length === 0, "ei JS-virheitä: " + errors.join(" | "));
  await browser.close();
  console.log(ok.map(s => "  OK   " + s).join("\n"));
  if (fail.length) {
    console.log(fail.map(s => "  FAIL " + s).join("\n"));
    process.exit(1);
  }
  console.log("\nSelaintestit OK (" + ok.length + ")");
})();
