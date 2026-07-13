# Maailman kartta 🚁

C64-henkinen maantiedon etsintäpeli: lennä helikopterilla ja etsi kaupungit,
maat, kunnat ja luonnonkohteet kartalta. Suomi, kuusi maanosaa ja Manner-Suomen
18 maakuntaa kuntineen, aikahyökkäys- ja opettelumuodot. Toimii puhelimessa
webappina, myös offline.

**Pelaa: https://peteyvonguldenstein.github.io/maailman-kartta/**

Avaa linkki puhelimessa ja lisää peli aloitusnäytölle
(iPhone: Safari → jaa → *Lisää Koti-valikkoon*; Android: Chrome → ⋮ → *Asenna sovellus*)
— sen jälkeen peli toimii ilman verkkoyhteyttä.

Kartat: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
Kunta- ja maakuntarajat: [Tilastokeskus](https://geo.stat.fi/),
kuntapohjaiset tilastointialueet 2026 (CC BY 4.0).
Generointi: `build_world.py`, testit: `node test_game.js`.
