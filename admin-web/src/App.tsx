import { Alert, Card, Empty, Layout, Space, Spin, Typography } from 'antd'

const { Header, Content } = Layout
const { Title, Paragraph } = Typography

export default function App() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          background: '#001529',
        }}
      >
        <Title level={4} style={{ color: '#fff', margin: 0 }}>
          考研专业课师资平台 · 内部管理后台
        </Title>
      </Header>
      <Content style={{ padding: 24 }}>
        <Paragraph>当前为 S0-04 工程骨架，尚未接入业务数据。</Paragraph>
        <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
          <Card title="Loading">
            <Spin />
          </Card>
          <Card title="Error">
            <Alert
              type="error"
              showIcon
              message="演示错误"
              description="这是静态 UI 演示，不是真实请求失败。"
            />
          </Card>
          <Card title="Empty">
            <Empty description="暂无业务数据（静态演示）" />
          </Card>
        </Space>
      </Content>
    </Layout>
  )
}
