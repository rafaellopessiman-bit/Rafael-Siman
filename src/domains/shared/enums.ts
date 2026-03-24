/**
 * Enums compartilhados entre domínios — atlas_local
 *
 * Convenção MongoDB: enums armazenados como string lowercase.
 */

export enum DocumentStatus {
  PENDING = 'pending',
  INDEXED = 'indexed',
  FAILED = 'failed',
  ARCHIVED = 'archived',
}

export enum FileType {
  TXT = '.txt',
  MD = '.md',
  JSON = '.json',
  CSV = '.csv',
}
