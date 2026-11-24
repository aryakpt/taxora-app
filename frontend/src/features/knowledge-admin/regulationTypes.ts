/** Indonesian tax regulation types: the code stored with each document, its full name, and who issues it.
 * The issuer is filled in from the type (a PMK is issued by the Minister of Finance) and can still be edited,
 * e.g. for a joint regulation. Full names are the official Indonesian ones in both interface languages. */
export interface RegulationType {
  code: string
  name: string
  issuer: string
}

export const REGULATION_TYPES: RegulationType[] = [
  { code: 'UU', name: 'Undang-Undang', issuer: 'Presiden Republik Indonesia dengan persetujuan DPR RI' },
  { code: 'PP', name: 'Peraturan Pemerintah', issuer: 'Presiden Republik Indonesia' },
  { code: 'PMK', name: 'Peraturan Menteri Keuangan', issuer: 'Menteri Keuangan Republik Indonesia' },
  { code: 'PER', name: 'Peraturan Direktur Jenderal Pajak', issuer: 'Direktur Jenderal Pajak' },
  { code: 'SE', name: 'Surat Edaran Direktur Jenderal Pajak', issuer: 'Direktur Jenderal Pajak' },
  { code: 'KEP', name: 'Keputusan Direktur Jenderal Pajak', issuer: 'Direktur Jenderal Pajak' },
]

export const regulationType = (code: string | undefined) =>
  REGULATION_TYPES.find(type => type.code.toLowerCase() === (code ?? '').toLowerCase())

/** "Peraturan Menteri Keuangan" for "PMK"; the code itself for anything not in the list. */
export const regulationTypeName = (code: string | undefined) => regulationType(code)?.name ?? code ?? ''
