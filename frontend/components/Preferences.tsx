"use client";

import Icon from "./Icon";
import { L, useL, useLang } from "../lib/i18n";
import { useTheme, type ThemePref } from "../lib/theme";

export default function Preferences() {
  const { lang, setLang } = useLang();
  const { pref, setPref } = useTheme();
  const tr = useL();
  const themes: { key: ThemePref; en: string; id: string; icon: "sun" | "moon" | "monitor" }[] = [
    { key: "light", en: "Light", id: "Terang", icon: "sun" },
    { key: "dark", en: "Dark", id: "Gelap", icon: "moon" },
    { key: "system", en: "System", id: "Sistem", icon: "monitor" },
  ];
  return (
    <dl className="facts">
      <dt><L en="Language" id="Bahasa" /></dt>
      <dd>
        <div className="seg" role="group" aria-label={tr("Language", "Bahasa")}>
          <button type="button" aria-pressed={lang === "en"} onClick={() => setLang("en")}>English</button>
          <button type="button" aria-pressed={lang === "id"} onClick={() => setLang("id")}>Bahasa Indonesia</button>
        </div>
      </dd>
      <dt><L en="Appearance" id="Tampilan" /></dt>
      <dd>
        <div className="seg" role="group" aria-label={tr("Appearance", "Tampilan")}>
          {themes.map((t) => (
            <button key={t.key} type="button" aria-pressed={pref === t.key} onClick={() => setPref(t.key)}>
              <Icon name={t.icon} size={14} /> <L en={t.en} id={t.id} />
            </button>
          ))}
        </div>
      </dd>
    </dl>
  );
}
