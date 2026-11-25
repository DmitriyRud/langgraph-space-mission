import { useCallback } from 'react';
import { useMissionStore } from '../stores/missionStore';
import type { Language } from '../types/mission';
import en from './locales/en.json';
import ru from './locales/ru.json';

const LOCALES: Record<Language, Record<string, unknown>> = {
  en,
  ru,
};

function lookup(obj: Record<string, unknown>, key: string): string | null {
  let current: unknown = obj;
  for (const part of key.split('.')) {
    if (current && typeof current === 'object' && part in (current as Record<string, unknown>)) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return null;
    }
  }
  return typeof current === 'string' ? current : null;
}

export function translate(
  lang: Language,
  key: string,
  params?: Record<string, string | number>
): string {
  const template = lookup(LOCALES[lang], key) ?? lookup(LOCALES.en, key) ?? key;
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (_match, name: string) =>
    params[name] !== undefined ? String(params[name]) : `{${name}}`
  );
}

export function useI18n() {
  const language = useMissionStore((s) => s.language);
  const setLanguage = useMissionStore((s) => s.setLanguage);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) => translate(language, key, params),
    [language]
  );

  return { language, setLanguage, t };
}
