import React from 'react';
import { Card, Row, Col, Statistic, Spin } from 'antd';

const Dashboard = ({ statistics }) => {
  if (!statistics) return <Spin />;

  return (
    <div style={{ padding: 16 }}>
      <h2>統計ダッシュボード</h2>
      <Row gutter={16}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="総映画数" value={statistics.total_movies || 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="総視聴数" value={statistics.total_records || 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="最近90日" value={statistics.recent_90_days || 0} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="トップジャンル" value={statistics.top_genre || '-'} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
