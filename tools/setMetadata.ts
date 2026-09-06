// Era groupings and logo URLs for German Pokémon sets.
// Logos from pokemontcg.io (English equivalents).
// Era order matches pokemonkarte.de cycles.

const TCG = (id: string) => `https://images.pokemontcg.io/${id}/logo.png`;

export interface SetMeta {
  era: string;
  logo?: string;
  logoScale?: number;
  reverseTypes?: string[]; // undefined → ['reverse']; explizite Liste für Sets mit mehreren Reverse-Varianten
}

export const ERA_ORDER = [
  'Mega Entwicklung',
  'Karmesin & Purpur',
  'Schwert & Schild',
  'Sonne & Mond',
  'XY',
  'Schwarz & Weiß',
  'HeartGold & SoulSilver',
  'Platin',
  'Diamant & Perl',
  'EX-Serie',
  'E-Karten',
  'Neo',
  'Grundserie',
];

export const SET_METADATA: Record<string, SetMeta> = {
  // ── Karmesin & Purpur ───────────────────────────────────────────────
  '30th Anniversary Celebration':             { era: 'Karmesin & Purpur' },
  'Schwarze Blitze':                          { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/schwarze-blitze.png', reverseTypes: ['reverse_pokeball', 'reverse_masterball', 'reverse'] },
  'Weiße Flammen':                            { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/weisse-flammen.png', reverseTypes: ['reverse_pokeball', 'reverse_masterball', 'reverse'] },
  'Ewige Rivalen':                            { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/ewige-rivalen.png' },
  'Reisegefährten':                           { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/reisgefahrten.png' },
  'Prismatische Entwicklungen':               { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/prismatische-entwicklungen.png', reverseTypes: ['reverse_pokeball', 'reverse_masterball', 'reverse'] },
  'Stürmische Funken':                        { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/Sturmischen-Funken.png' },
  'Stellarkrone':                             { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/stellarkrone.png' },
  'Nebel der Sagen':                          { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/Nebel-der-Sagen-logo.png' },
  'Maskerade im Zwielicht':                   { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/Maskerade-im-Zwielicht-logo.png' },
  'Gewalten der Zeit':                        { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/Gewalten_der_Zeit-2.png' },
  'Paldeas Schicksale':                       { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/Paldeas-Schicksale-2.png' },
  'Paradoxrift':                              { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/paradoxrift.png' },
  'Pokémon 151':                              { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/pokemon-151.png' },
  'Obsidianflammen':                          { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/obsidian-flammen.png' },
  'Entwicklungen in Paldea':                  { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/entwicklungen-in-paldea.png' },
  'Karmesin & Purpur':                        { era: 'Karmesin & Purpur', logo: 'https://images.poketrack.de/karmesin-purpur.png' },
  'Karmesin & Purpur Promos':                 { era: 'Karmesin & Purpur', logo: TCG('svp') },

  // ── Mega Entwicklung ────────────────────────────────────────────────
  'Wachsendes Chaos':                         { era: 'Mega Entwicklung', logo: 'https://images.poketrack.de/wachsendes-chaos.png' },
  'Optimale Ordnung':                         { era: 'Mega Entwicklung', logo: 'https://images.poketrack.de/optimale_ordnung.png' },
  'Erhabene Helden':                          { era: 'Mega Entwicklung', logo: 'https://images.poketrack.de/erhabene-helden.png', reverseTypes: ['reverse_energie', 'reverse_pokeball'] },
  'Fatale Flammen':                           { era: 'Mega Entwicklung', logo: 'https://images.poketrack.de/Fatale-Flammen-Logo.png' },
  'Mega-Entwicklung':                         { era: 'Mega Entwicklung', logo: 'https://images.poketrack.de/Mega-Entwicklung.png' },
  'Dunkelnacht':                              { era: 'Mega Entwicklung', logo: 'https://images.poketrack.de/dunkel-nacht-1781868747.png' },
  'Mega Entwicklung Promos':                  { era: 'Mega Entwicklung' },

  // ── Schwert & Schild ────────────────────────────────────────────────
  'Zenit der Könige':                         { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/zenit-der-konige-erweiterung.png' },
  'Zenit der Könige - Galar-Galerie':         { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/zenit-der-konige-erweiterung.png' },
  'Silberne Sturmwinde':                      { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/silberne-sturmwinde-erweiterung-1.png' },
  'Silberne Sturmwinde - Trainergalerie':     { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/silberne-sturmwinde-erweiterung-1.png' },
  'Verlorener Ursprung':                      { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/verlorener-ursprung-erweiterung-1.png' },
  'Verlorener Ursprung - Trainergalerie':     { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/verlorener-ursprung-erweiterung-1.png' },
  'Pokémon GO':                               { era: 'Schwert & Schild', logo: TCG('pgo') },
  'Astralglanz':                              { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/astralglanz-erweiterung.png' },
  'Astralglanz - Trainergalerie':             { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/astralglanz-erweiterung.png' },
  'Strahlende Sterne':                        { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/strahlende-sterne.png' },
  'Strahlende Sterne - Trainergalerie':       { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/strahlende-sterne.png' },
  'Fusionsangriff':                           { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/fusions.png' },
  'Celebrations':                             { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/celebrations-en-set-1.png' },
  'Celebrations - Klassische Sammlung':       { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/celebrations-classic-collection-en-set.png' },
  'Drachenwandel':                            { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/Drachenwandel.png' },
  'Schaurige Herrschaft':                     { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/s-hersschaft.png' },
  'Kampfstile':                               { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/kampfstile.png' },
  'Glänzendes Schicksal':                     { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/glanzendes-schicksal.png' },
  'Glänzendes Schicksal - Schillernde Schatzkammer': { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/glanzendes-schicksal.png' },
  'Farbenschock':                             { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/farbenschock.png' },
  'Weg des Champs':                           { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/weg-des-champs.png' },
  'Flammende Finsternis':                     { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/flammende-finsternis.png' },
  'Clash der Rebellen':                       { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/rebellen.png' },
  'Schwert & Schild':                         { era: 'Schwert & Schild', logo: 'https://images.poketrack.de/schwert.png' },
  'Schwert & Schild Promos':                  { era: 'Schwert & Schild', logo: TCG('swshp') },

  // ── Sonne & Mond ────────────────────────────────────────────────────
  'Welten im Wandel':                         { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/welten-im-wandel-erweiterung-1.png' },
  'Verborgenes Schicksal':                    { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/verborgenes-schicksal-erweiterung.png' },
  'Verborgenes Schicksal - Schillernde Schatzkammer': { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/verborgenes-schicksal-erweiterung.png' },
  'Bund der Gleichgesinnten':                 { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/bund-der-gleichgesinnten-erweiterung-1.png' },
  'Kräfte im Einklang':                       { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/Krafte_im_Einklang.png' },
  'Meisterdetektiv Pikachu':                  { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/meisterdetektiv-pikachu-erweiterung-1.png' },
  'Teams sind Trumpf':                        { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/teams-sind-trumpf-erweiterung.png' },
  'Echo des Donners':                         { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/echo-des-donners-erweiterung.png' },
  'Majestät der Drachen':                     { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/Majestat_der_Drachen.png' },
  'Sturm am Firmament':                       { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/sturm-am-firmament-erweiterung.png' },
  'Grauen der Lichtfinsternis':               { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/grauen-der-lichtfinsternis-erweiterung-1.png' },
  'Ultraprisma':                              { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/ultra-prisma-erweiterung.png' },
  'Aufziehen der Sturmröte':                  { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/Aufziehen_der_Sturmrote-1.png' },
  'Schimmernde Legenden':                     { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/schimmernde-legenden-erweiterung-1.png' },
  'Nacht in Flammen':                         { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/nacht-in-flammen-erweiterung.png' },
  'Stunde der Wächter':                       { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/Stunde-der-wachter-1.png' },
  'Sonne & Mond':                             { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/sonne-mond-erweiterung-1.png' },
  'Sonne & Mond Promos':                      { era: 'Sonne & Mond', logo: 'https://images.poketrack.de/sonne-mond-erweiterung-1.png' },

  // ── XY-Serie ────────────────────────────────────────────────────────
  'Evolution':                                { era: 'XY', logo: 'https://images.poketrack.de/evolution-erweiterung-1.png' },
  'Dampfkessel':                              { era: 'XY', logo: 'https://images.poketrack.de/dampfkessel-erweiterung-1.png' },
  'Schicksalsschmiede':                       { era: 'XY', logo: 'https://images.poketrack.de/schicksalsschmiede-erweiterung.png' },
  'Generationen':                             { era: 'XY', logo: 'https://images.poketrack.de/generationen-erweiterung-1.png' },
  'TURBOfieber':                              { era: 'XY', logo: 'https://images.poketrack.de/turbofieber-erweiterung.png' },
  'TURBOstart':                               { era: 'XY', logo: 'https://images.poketrack.de/turbostart-erweiterung.png' },
  'Ewiger Anfang':                            { era: 'XY', logo: 'https://images.poketrack.de/ewiger-anfang-erweiterung.png' },
  'Drachenleuchten':                          { era: 'XY', logo: 'https://images.poketrack.de/drachenleuchten-erweiterung-1.png' },
  'Protoschock':                              { era: 'XY', logo: 'https://images.poketrack.de/protoschock-erweiterung.png' },
  'Phantomkräfte':                            { era: 'XY', logo: 'https://images.poketrack.de/Phantomkrafte.png' },
  'Fliegende Fäuste':                         { era: 'XY', logo: 'https://images.poketrack.de/Fliegende_Fauste-1.png' },
  'Flammenmeer':                              { era: 'XY', logo: 'https://images.poketrack.de/flammenmeer-erweiterung-1.png' },
  'XY':                                       { era: 'XY', logo: TCG('xy1') },
  'Willkommen in Kalos':                      { era: 'XY', logo: 'https://images.poketrack.de/willkommen-in-kalos-erweiterung.png' },
  'XY Promos':                                { era: 'XY', logo: TCG('xyp') },

  // ── Schwarz & Weiß ──────────────────────────────────────────────────

  'Plasma-Blaster':                           { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/plasma-blaster-erweiterung-1.png' },
  'Plasma-Frost':                             { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/plasma-frost-erweiterung-1.png' },
  'Plasma-Sturm':                             { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/plasma-sturm-erweiterung-1.png' },
  'Überschrittene Schwellen':                 { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/Uberschrittene_Schwellen-1.png' },

  'Hoheit der Drachen':                       { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/hoheit-der-drachen-erweiterung.png' },
  'Erforscher der Finsternis':                { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/erforscher-der-finsternis-erweiterung-1-1.png' },
  'Kommende Schicksale':                      { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/kommende-schicksale-erweiterung-1.png' },
  'Königliche Siege':                         { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/Konigliche_Siege-1.png' },
  'Aufstreben der Mächte':                    { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/Aufstreben_der_Machtigen-1-1.png' },
  'Schwarz & Weiß':                           { era: 'Schwarz & Weiß', logo: 'https://images.poketrack.de/schwarz-weiss-erweiterung-1-1.png' },
  'Schwarz & Weiß Promos':                    { era: 'Schwarz & Weiß', logo: TCG('bwp') },

  // ── HeartGold & SoulSilver ──────────────────────────────────────────
  'Ruf der Legenden':                         { era: 'HeartGold & SoulSilver', logo: 'https://images.poketrack.de/ruf.png' },
  'Triumph':                                  { era: 'HeartGold & SoulSilver', logo: 'https://images.poketrack.de/triumph.png' },
  'Unerschrocken':                            { era: 'HeartGold & SoulSilver', logo: 'https://images.poketrack.de/unerschrocken.png' },
  'Entfesselt':                               { era: 'HeartGold & SoulSilver', logo: 'https://images.poketrack.de/entfesselt.png' },
  'HeartGold & SoulSilver Promos':            { era: 'HeartGold & SoulSilver', logo: 'https://images.poketrack.de/hgss-promos-1-1.png' },
  'HeartGold & SoulSilver':                   { era: 'HeartGold & SoulSilver', logo: TCG('hgss1') },

  // ── Platin-Serie ────────────────────────────────────────────────────
  'Arceus':                                   { era: 'Platin', logo: 'https://images.poketrack.de/Platin-Arceus.webp', logoScale: 2 },
  'Ultimative Sieger':                        { era: 'Platin', logo: 'https://images.poketrack.de/ulti-siege.png' },
  'Aufstieg der Rivalen':                     { era: 'Platin', logo: 'https://images.poketrack.de/aufstieg-der-rivalen.png' },
  'Platin':                                   { era: 'Platin', logo: 'https://images.poketrack.de/platin.png' },

  // ── Diamant & Perl ──────────────────────────────────────────────────
  'Sturmtief':                                { era: 'Diamant & Perl', logo: 'https://images.poketrack.de/sturmtief.png' },
  'Erwachte Legenden':                        { era: 'Diamant & Perl', logo: 'https://images.poketrack.de/erwachte-legenden.png' },
  'Majestätischer Morgen':                    { era: 'Diamant & Perl', logo: 'https://images.poketrack.de/m-morgen.png' },
  'Epische Begegnungen':                      { era: 'Diamant & Perl', logo: 'https://images.poketrack.de/epische-begegnungen.png' },
  'Rätselhafte Wunder':                       { era: 'Diamant & Perl', logo: 'https://images.poketrack.de/ratselhafte-wunder.png' },
  'Geheimnisvolle Schätze':                   { era: 'Diamant & Perl', logo: 'https://images.poketrack.de/geh-schatze.png' },
  'Diamant & Perl Promos':                    { era: 'Diamant & Perl', logo: TCG('dpp') },
  'Diamant & Perl':                           { era: 'Diamant & Perl', logo: 'https://images.poketrack.de/diamant-perl.png' },

  // ── EX-Serie ────────────────────────────────────────────────────────
  'EX Power Keepers':                         { era: 'EX-Serie', logo: TCG('ex16') },
  'EX Dragon Frontiers':                      { era: 'EX-Serie', logo: TCG('ex15') },
  'EX Crystal Guardians':                     { era: 'EX-Serie', logo: TCG('ex14') },
  'EX Holo Phantoms':                         { era: 'EX-Serie', logo: TCG('ex13') },
  'EX Legend Maker':                          { era: 'EX-Serie', logo: TCG('ex12') },
  'EX Delta Species':                         { era: 'EX-Serie', logo: 'https://images.poketrack.de/delta-species-en-set-1.png' },
  'EX Verborgene Mächte':                     { era: 'EX-Serie', logo: 'https://images.poketrack.de/verborgene-machte.png' },
  'EX Smaragd':                               { era: 'EX-Serie', logo: 'https://images.poketrack.de/smaragd.png' },
  'EX Deoxys':                                { era: 'EX-Serie', logo: 'https://images.poketrack.de/deoxys-en-set-1.png' },
  'EX Feuerrot & Blattgrün':                  { era: 'EX-Serie', logo: 'https://images.poketrack.de/feuerrot%20%26%20blatgr%C3%BCn.png' },
  'EX Team Magma vs Team Aqua':               { era: 'EX-Serie', logo: TCG('ex4') },
  'EX Drache':                                { era: 'EX-Serie', logo: 'https://images.poketrack.de/Drache.png' },
  'EX Sandsturm':                             { era: 'EX-Serie', logo: 'https://images.poketrack.de/sandsturm.png' },
  'EX Rubin & Saphir':                        { era: 'EX-Serie', logo: 'https://images.poketrack.de/rubin%20%26%20saphir.png' },

  // ── E-Karten ────────────────────────────────────────────────────────
  'Skyridge':                                 { era: 'E-Karten', logo: 'https://images.poketrack.de/skyridge-en-set-1.png' },
  'Aquapolis':                                { era: 'E-Karten', logo: 'https://images.poketrack.de/aquapolis-en-set-1.png' },
  'Expedition':                               { era: 'E-Karten', logo: 'https://images.poketrack.de/expedition-en-set-1.png' },

  // ── Neo-Serie ───────────────────────────────────────────────────────
  'Neo Genesis':                              { era: 'Neo', logo: TCG('neo1') },
  'Neo Entdeckung':                           { era: 'Neo', logo: 'https://images.poketrack.de/neo-entdeckung.png' },
  'Neo Revelation':                           { era: 'Neo', logo: TCG('neo3') },
  'Neo Destiny':                              { era: 'Neo', logo: TCG('neo4') },

  // ── Grundserie ──────────────────────────────────────────────────────
  'Team Rocket':                              { era: 'Grundserie', logo: TCG('base5') },
  'Fossil':                                   { era: 'Grundserie', logo: TCG('base3') },
  'Dschungel':                                { era: 'Grundserie', logo: TCG('base2') },
  'Basisset':                                 { era: 'Grundserie', logo: TCG('base1') },
};

export function getSetMeta(setName: string): SetMeta {
  return SET_METADATA[setName] ?? { era: 'Weitere Sets' };
}
