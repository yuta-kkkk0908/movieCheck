import React, { useState, useEffect } from 'react';
import { Layout, Tabs, Button, Input, Card, Rate, Tag, Modal, Form, Select, DatePicker, message, Spin } from 'antd';
import { SearchOutlined, PlusOutlined, SyncOutlined } from '@ant-design/icons';
import axios from 'axios';
import './App.css';

const { Header, Content, Footer, Sider } = Layout;
import Dashboard from './components/Dashboard';

const API_BASE = 'http://localhost:8001/api';

function App() {
  const [movies, setMovies] = useState([]);
  const [records, setRecords] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isRecordModalVisible, setIsRecordModalVisible] = useState(false);
  const [isSyncModalVisible, setIsSyncModalVisible] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
    const [statistics, setStatistics] = useState(null);
    const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [form] = Form.useForm();
  const [syncForm] = Form.useForm();

  // 初期データ読み込み
  useEffect(() => {
    loadMovies();
    loadRecords();
      loadStatistics();
  }, []);

  const loadMovies = async () => {
    try {
      const response = await axios.get(`${API_BASE}/movies/`);
      setMovies(response.data);
    } catch (error) {
      console.error('映画読み込みエラー:', error);
      message.error('映画の読み込みに失敗しました');
    }
  };

  const loadRecords = async () => {
    try {
      const response = await axios.get(`${API_BASE}/records/`);
      setRecords(response.data);
    } catch (error) {
      console.error('記録読み込みエラー:', error);
      message.error('記録の読み込みに失敗しました');
    }
  };

    const loadStatistics = async () => {
      setIsLoadingStats(true);
      try {
        const response = await axios.get(`${API_BASE}/statistics/overview`);
        setStatistics(response.data);
      } catch (error) {
        console.error('統計読み込みエラー:', error);
      } finally {
        setIsLoadingStats(false);
      }
    };

  const handleSearch = async () => {
    if (!searchQuery) return;
    
    setIsSearching(true);
    try {
         const response = await axios.post(`${API_BASE}/search/movies`, {
           query: searchQuery
         });
         setSearchResults(response.data);
         if (response.data.length === 0) {
           message.info('検索結果がありません');
         }
    } catch (error) {
      console.error('検索エラー:', error);
      message.error('検索に失敗しました');
    } finally {
      setIsSearching(false);
    }
  };

  const registerMovieFromSearch = async (movie) => {
    try {
      const resp = await axios.post(`${API_BASE}/search/register`, movie);
      if (resp.data && resp.data.success) {
        const movieId = resp.data.movie_id;
        // 取得したIDで詳細を取得して選択
        const detailResp = await axios.get(`${API_BASE}/movies/${movieId}`);
        setSelectedMovie(detailResp.data);
        setIsRecordModalVisible(true);
        // 更新
        loadMovies();
      } else {
        message.error(resp.data?.message || '映画の登録に失敗しました');
      }
    } catch (error) {
      console.error('映画登録エラー:', error);
      message.error('映画の登録に失敗しました');
    }
  };

  const handleRegisterRecord = async (values) => {
    try {
      await axios.post(`${API_BASE}/records/`, {
        movie_id: selectedMovie.id,
        viewed_date: values.viewed_date.toISOString(),
        viewing_method: values.viewing_method,
        rating: values.rating,
        mood: values.mood,
        comment: values.comment
      });
      
      message.success('記録を保存しました');
      setIsRecordModalVisible(false);
      form.resetFields();
      loadRecords();
    } catch (error) {
      console.error('記録作成エラー:', error);
      message.error('記録の保存に失敗しました');
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      // 対話型ログイン（credentialsなし）でAPIを呼び出し
      const response = await axios.post(`${API_BASE}/search/sync`, {
        email: null,
        password: null
      });

      if (response.data.success) {
        message.success(`同期完了: 新規${response.data.added}件、既存${response.data.existing}件`);
        setIsSyncModalVisible(false);
        syncForm.resetFields();
        loadMovies();
        loadRecords();
      } else {
        message.error(response.data.message);
      }
    } catch (error) {
      console.error('同期エラー:', error);
      message.error('同期に失敗しました。ブラウザの操作確認をしてください。');
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0 }}>🎬 映画視聴管理</h1>
        <Button 
          type="primary" 
          icon={<SyncOutlined />}
          onClick={() => setIsSyncModalVisible(true)}
          loading={isSyncing}
        >
          映画.comから同期
        </Button>
      </Header>
      
      <Layout>
        <Content style={{ padding: '20px' }}>
          <Tabs
            items={[
              {
                 key: 'dashboard',
                 label: 'ダッシュボード',
                 children: <Dashboard statistics={statistics} />
               },
               {
                key: 'home',
                label: 'トップ',
                children: (
                  <div>
                    <h2>最近の視聴記録</h2>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '20px' }}>
                      {records.slice(0, 9).map(record => {
                        const movie = movies.find(m => m.id === record.movie_id);
                        return (
                          <Card key={record.id} hoverable>
                            <h3>{movie?.title || '不明'}</h3>
                            {record.rating && <Rate disabled value={record.rating} />}
                            <p>視聴日: {new Date(record.viewed_date).toLocaleDateString('ja-JP')}</p>
                            <Tag color="blue">{record.viewing_method}</Tag>
                            {record.mood && <Tag color="cyan">{record.mood}</Tag>}
                          </Card>
                        );
                      })}
                    </div>
                  </div>
                )
              },
              {
                key: 'search',
                label: '映画検索',
                children: (
                  <div>
                    <Input.Search
                      placeholder="映画タイトルを入力..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onSearch={handleSearch}
                      enterButton={<Button type="primary" icon={<SearchOutlined />}>検索</Button>}
                      size="large"
                      style={{ marginBottom: '20px' }}
                      loading={isSearching}
                    />
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '20px' }}>
                      {searchResults.map((movie, idx) => (
                        <Card
                          key={idx}
                          hoverable
                        >
                          <h3>{movie.title}</h3>
                          <p>公開年: {movie.released_year}</p>
                          <p>{movie.genre}</p>
                           {movie.image_url && (
                             <img src={movie.image_url} style={{ width: '100%', height: '150px', objectFit: 'cover', marginBottom: '10px' }} alt={movie.title} />
                           )}
                           <div style={{ marginTop: '10px', display: 'flex', gap: '5px' }}>
                             <Button type="primary" size="small" style={{ flex: 1 }} onClick={() => registerMovieFromSearch(movie)}>
                               登録して記録
                             </Button>
                          </div>
                        </Card>
                      ))}
                    </div>
                  </div>
                )
              },
              {
                key: 'records',
                label: '記録一覧',
                children: (
                  <div>
                    <Button type="primary" icon={<PlusOutlined />} style={{ marginBottom: '20px' }}>
                      新規記録
                    </Button>
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ borderBottom: '2px solid #ddd' }}>
                            <th style={{ padding: '10px', textAlign: 'left' }}>映画タイトル</th>
                            <th style={{ padding: '10px', textAlign: 'left' }}>視聴日</th>
                            <th style={{ padding: '10px', textAlign: 'left' }}>視聴方法</th>
                            <th style={{ padding: '10px', textAlign: 'left' }}>評価</th>
                            <th style={{ padding: '10px', textAlign: 'left' }}>気分</th>
                          </tr>
                        </thead>
                        <tbody>
                          {records.map(record => {
                            const movie = movies.find(m => m.id === record.movie_id);
                            return (
                              <tr key={record.id} style={{ borderBottom: '1px solid #ddd' }}>
                                <td style={{ padding: '10px' }}>{movie?.title || '不明'}</td>
                                <td style={{ padding: '10px' }}>{new Date(record.viewed_date).toLocaleDateString('ja-JP')}</td>
                                <td style={{ padding: '10px' }}>{record.viewing_method}</td>
                                <td style={{ padding: '10px' }}>
                                  {record.rating && <Rate disabled value={record.rating} />}
                                </td>
                                <td style={{ padding: '10px' }}>
                                  {record.mood && <Tag>{record.mood}</Tag>}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )
              }
            ]}
          />
        </Content>
      </Layout>

      {/* 記録登録モーダル */}
      <Modal
        title="視聴記録を登録"
        open={isRecordModalVisible}
        onCancel={() => setIsRecordModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleRegisterRecord}
        >
          <Form.Item label="視聴方法" name="viewing_method" rules={[{ required: true, message: '視聴方法を選択してください' }]}>
            <Select placeholder="選択してください">
              <Select.Option value="theater">映画館</Select.Option>
              <Select.Option value="streaming">ストリーミング</Select.Option>
              <Select.Option value="tv">TV放送</Select.Option>
              <Select.Option value="dvd">DVD/Blu-ray</Select.Option>
              <Select.Option value="other">その他</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="視聴日" name="viewed_date" rules={[{ required: true, message: '視聴日を選択してください' }]}>
            <DatePicker />
          </Form.Item>

          <Form.Item label="評価" name="rating">
            <Rate />
          </Form.Item>

          <Form.Item label="気分" name="mood">
            <Select placeholder="選択してください">
              <Select.Option value="happy">楽しい</Select.Option>
              <Select.Option value="sad">悲しい</Select.Option>
              <Select.Option value="excited">興奮</Select.Option>
              <Select.Option value="relaxed">リラックス</Select.Option>
              <Select.Option value="thoughtful">考察的</Select.Option>
              <Select.Option value="scary">怖い</Select.Option>
              <Select.Option value="romantic">ロマンティック</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item label="コメント" name="comment">
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 映画.com同期モーダル */}
      <Modal
        title="映画.comから同期"
        open={isSyncModalVisible}
        onCancel={() => setIsSyncModalVisible(false)}
        okText="同期開始"
        cancelText="キャンセル"
        onOk={handleSync}
        confirmLoading={isSyncing}
      >
        <Spin spinning={isSyncing} tip="ブラウザを起動中...ログインしてください">
          <div style={{ padding: '20px', backgroundColor: '#f0f5ff', borderRadius: '4px', marginBottom: '20px' }}>
            <h3>🔍 同期手順</h3>
            <ol style={{ marginLeft: '20px' }}>
              <li>「同期開始」ボタンをクリックするとブラウザが起動します</li>
              <li>映画.com のログイン画面が表示されます</li>
              <li>その画面でログイン方法を選んでください（メール、Facebook、Google等）</li>
              <li>認証が完了したら、自動的に視聴履歴が取得されます（完了直前の画面を閉じないでください）</li>
            </ol>
            <p style={{ marginTop: '10px', color: '#999', fontSize: '12px' }}>
              🔐 パスワードはこのアプリに送信されません。認証等を直接映画.comで実施してください。
            </p>
          </div>
        </Spin>
      </Modal>
    </Layout>
  );
}

export default App;
