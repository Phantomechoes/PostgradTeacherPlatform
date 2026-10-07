import { Tag } from 'antd'
import type { AvailabilityStatus, VerificationStatus } from '../../api/types'
import { AVAILABILITY_LABEL, VERIFICATION_LABEL } from './labels'

export function AvailabilityTag({ value }: { value: AvailabilityStatus }) {
  const color =
    value === 'available' ? 'green' : value === 'unavailable' ? 'red' : 'gold'
  return <Tag color={color}>{AVAILABILITY_LABEL[value]}</Tag>
}

export function VerificationTag({ value }: { value: VerificationStatus }) {
  const color =
    value === 'verified' ? 'blue' : value === 'rejected' ? 'red' : 'default'
  return <Tag color={color}>{VERIFICATION_LABEL[value]}</Tag>
}
