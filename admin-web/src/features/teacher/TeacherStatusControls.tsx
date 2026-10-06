import { Select, Space, Typography } from 'antd'
import type { AvailabilityStatus, VerificationStatus } from '../../api/types'
import { EntityStatusAction } from '../../components/EntityStatusAction'
import { StatusTag } from '../../components/StatusTag'
import {
  AVAILABILITY_LABEL,
  AVAILABILITY_VALUES,
  VERIFICATION_LABEL,
  VERIFICATION_VALUES,
} from './labels'

export type TeacherHeaderMutation =
  'profile' | 'status' | 'availability' | 'verification'

export function TeacherStatusControls({
  active,
  availability,
  verification,
  saving,
  onStatus,
  onAvailability,
  onVerification,
}: {
  active: boolean
  availability: AvailabilityStatus
  verification: VerificationStatus
  saving: TeacherHeaderMutation | null
  onStatus: (active: boolean) => void
  onAvailability: (value: AvailabilityStatus) => void
  onVerification: (value: VerificationStatus) => void
}) {
  const busy = saving !== null
  return (
    <Space orientation="vertical" size="middle">
      <Space wrap align="center">
        <Typography.Text>档案状态</Typography.Text>
        <StatusTag mode="entity" active={active} />
        <EntityStatusAction
          active={active}
          loading={saving === 'status'}
          disabled={busy && saving !== 'status'}
          confirmTitle="确认停用该师资？"
          description="停用不会删除历史数据。"
          onChange={onStatus}
        />
      </Space>
      <Space wrap align="center">
        <Typography.Text>可授课状态</Typography.Text>
        <Select<AvailabilityStatus>
          style={{ width: 160 }}
          value={availability}
          disabled={busy}
          loading={saving === 'availability'}
          onChange={(value) => {
            if (value !== availability) {
              onAvailability(value)
            }
          }}
          options={AVAILABILITY_VALUES.map((value) => ({
            value,
            label: AVAILABILITY_LABEL[value],
          }))}
        />
      </Space>
      <Space wrap align="center">
        <Typography.Text>核验状态</Typography.Text>
        <Select<VerificationStatus>
          style={{ width: 160 }}
          value={verification}
          disabled={busy}
          loading={saving === 'verification'}
          onChange={(value) => {
            if (value !== verification) {
              onVerification(value)
            }
          }}
          options={VERIFICATION_VALUES.map((value) => ({
            value,
            label: VERIFICATION_LABEL[value],
          }))}
        />
      </Space>
    </Space>
  )
}
