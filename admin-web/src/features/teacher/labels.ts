import type { AvailabilityStatus, VerificationStatus } from '../../api/types'

export const AVAILABILITY_LABEL: Record<AvailabilityStatus, string> = {
  unknown: '未知',
  available: '可授课',
  unavailable: '不可授课',
}

export const VERIFICATION_LABEL: Record<VerificationStatus, string> = {
  unverified: '未核验',
  verified: '已核验',
  rejected: '已拒绝',
}

export const AVAILABILITY_VALUES = [
  'unknown',
  'available',
  'unavailable',
] as const satisfies readonly AvailabilityStatus[]

export const VERIFICATION_VALUES = [
  'unverified',
  'verified',
  'rejected',
] as const satisfies readonly VerificationStatus[]
