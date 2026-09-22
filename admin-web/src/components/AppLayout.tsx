import { Layout, Menu, Typography } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

const { Header, Sider, Content } = Layout

function selectedKey(pathname: string): string {
  if (pathname.startsWith('/exam-subjects/national')) {
    return '/exam-subjects/national'
  }
  if (pathname.startsWith('/catalogs')) {
    return '/catalogs'
  }
  if (pathname.startsWith('/schools')) {
    return '/schools'
  }
  return ''
}

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const current = selectedKey(location.pathname)

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={0}>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={current ? [current] : []}
          defaultOpenKeys={['master-data', 'catalogs']}
          onClick={({ key }) => {
            if (key.startsWith('/')) {
              navigate(key)
            }
          }}
          items={[
            {
              key: 'master-data',
              label: '主数据',
              children: [
                { key: '/schools', label: '院校' },
                { key: '/exam-subjects/national', label: '全国统考科目' },
              ],
            },
            {
              key: 'catalogs',
              label: '招生目录',
              children: [{ key: '/catalogs', label: '招生目录' }],
            },
          ]}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            background: '#001529',
            paddingInline: 24,
            overflow: 'hidden',
          }}
        >
          <Typography.Title
            level={4}
            ellipsis
            style={{ color: '#fff', margin: 0, minWidth: 0, flex: 1 }}
          >
            考研专业课师资平台 · 内部管理后台
          </Typography.Title>
          <Typography.Text
            style={{ color: '#ffffffd9', flexShrink: 0, whiteSpace: 'nowrap' }}
          >
            Local Admin · No Auth
          </Typography.Text>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
