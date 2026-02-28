import React, { useState, useEffect, useMemo } from 'react';
import { Layout, Tabs, Button, Input, Card, Rate, Tag, Modal, Form, Select, DatePicker, message, Spin, Space, Checkbox, Table } from 'antd';
import { SearchOutlined, PlusOutlined, SyncOutlined, EditOutlined, DeleteOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import dayjs from 'dayjs';
import './App.css';

const { Header, Content, Footer, Sider } = Layout;
import Dashboard from './components/Dashboard';

const API_BASE = 'http://localhost:8001/api';
const VIEWING_METHOD_LABELS = {
  theater: '映画館',
  streaming: 'ストリーミング',
  tv: 'TV放送',
  dvd: 'DVD/Blu-ray',
  other: 'その他'
};
const MOOD_LABELS = {
  happy: '楽しい',
  sad: '悲しい',
  excited: '興奮',
  relaxed: 'リラックス',
  thoughtful: '考察的',
  scary: '怖い',
  romantic: 'ロマンティック'
};

function App() {
  const [movies, setMovies] = useState([]);
  const [records, setRecords] = useState([]);
  const [selectedRecordIds, setSelectedRecordIds] = useState([]);
  const [recordQuickSearch, setRecordQuickSearch] = useState('');
  const [displayedRecordCount, setDisplayedRecordCount] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [headerSearchQuery, setHeaderSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [activeTabKey, setActiveTabKey] = useState('dashboard');
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isRecordModalVisible, setIsRecordModalVisible] = useState(false);
  const [isSyncModalVisible, setIsSyncModalVisible] = useState(false);
  const [savedCredential, setSavedCredential] = useState(null);
  const [isCredentialLoading, setIsCredentialLoading] = useState(false);
  const [isEditRecordModalVisible, setIsEditRecordModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
    const [statistics, setStatistics] = useState(null);
    const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [form] = Form.useForm();
  const [recordEditForm] = Form.useForm();
  const [syncForm] = Form.useForm();

  const movieMap = useMemo(() => {
    return new Map(movies.map((movie) => [movie.id, movie]));
  }, [movies]);

  const searchableRecords = useMemo(() => {
    const keyword = recordQuickSearch.trim().toLowerCase();
    return records
      .map((record) => {
        const movie = movieMap.get(record.movie_id);
        return {
          ...record,
          movie_title: movie?.title || '不明',
          released_year: movie?.released_year ?? null,
          director: movie?.director || '',
          viewing_method_label: VIEWING_METHOD_LABELS[record.viewing_method] || record.viewing_method || '-',
          mood_label: MOOD_LABELS[record.mood] || record.mood || '-'
        };
      })
      .filter((record) => {
        if (!keyword) return true;
        const text = [
          record.movie_title,
          String(record.released_year ?? ''),
          record.director,
          record.viewing_method_label,
          record.mood_label,
          record.comment || ''
        ]
          .join(' ')
          .toLowerCase();
        return text.includes(keyword);
      });
  }, [records, movieMap, recordQuickSearch]);

  // 初期データ読み込み
  useEffect(() => {
    loadMovies();
    loadRecords();
      loadStatistics();
  }, []);

  useEffect(() => {
    if (isSyncModalVisible) {
      loadSavedCredential();
    }
  }, [isSyncModalVisible]);

  useEffect(() => {
    // レコード再読込後に存在しないIDが残らないよう選択状態を同期する
    setSelectedRecordIds((prevIds) => prevIds.filter((id) => records.some((record) => record.id === id)));
  }, [records]);

  useEffect(() => {
    setDisplayedRecordCount(searchableRecords.length);
  }, [searchableRecords]);

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

  const loadSavedCredential = async () => {
    setIsCredentialLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/credentials/eiga`);
      setSavedCredential(response.data);
    } catch (error) {
      console.error('資格情報取得エラー:', error);
      setSavedCredential(null);
    } finally {
      setIsCredentialLoading(false);
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

  const executeSearch = async (query, options = {}) => {
    const { switchToSearchTab = false } = options;
    const normalizedQuery = query?.trim();
    if (!normalizedQuery) return;

    if (switchToSearchTab) {
      setActiveTabKey('search');
    }

    setIsSearching(true);
    try {
         const response = await axios.post(`${API_BASE}/search/movies`, {
           query: normalizedQuery
         });
         setSearchQuery(normalizedQuery);
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

  const handleHeaderSearch = async () => {
    await executeSearch(headerSearchQuery, { switchToSearchTab: true });
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

  const extractValidationMessage = (error, fallback) => {
    const details = error?.response?.data?.detail;
    if (Array.isArray(details)) {
      return details
        .map((item) => {
          const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : 'field';
          return `${field}: ${item?.msg || 'invalid'}`;
        })
        .join(' / ');
    }
    if (typeof details === 'string') {
      return details;
    }
    return fallback;
  };

  const openEditRecordModal = (record) => {
    setEditingRecord(record);
    recordEditForm.setFieldsValue({
      viewed_date: dayjs(record.viewed_date),
      viewing_method: record.viewing_method,
      rating: record.rating ?? undefined,
      mood: record.mood ?? undefined,
      comment: record.comment ?? ''
    });
    setIsEditRecordModalVisible(true);
  };

  const handleUpdateRecord = async (values) => {
    if (!editingRecord) return;
    try {
      await axios.patch(`${API_BASE}/records/${editingRecord.id}`, {
        viewed_date: values.viewed_date.toISOString(),
        viewing_method: values.viewing_method,
        rating: values.rating ?? null,
        mood: values.mood ?? null,
        comment: values.comment ?? null
      });
      message.success('記録を更新しました');
      setIsEditRecordModalVisible(false);
      setEditingRecord(null);
      recordEditForm.resetFields();
      loadRecords();
    } catch (error) {
      console.error('記録更新エラー:', error);
      message.error(extractValidationMessage(error, '記録の更新に失敗しました'));
    }
  };

  const handleDeleteRecord = (recordId) => {
    Modal.confirm({
      title: '記録を削除しますか？',
      icon: <ExclamationCircleOutlined />,
      content: 'この操作は元に戻せません。',
      okText: '削除',
      okType: 'danger',
      cancelText: 'キャンセル',
      onOk: async () => {
        const { successIds, failedIds } = await deleteRecordsByIds([recordId]);
        if (successIds.length > 0) {
          message.success('記録を削除しました');
          setSelectedRecordIds((prevIds) => prevIds.filter((id) => id !== recordId));
          await loadRecords();
        }
        if (failedIds.length > 0) {
          message.error('記録の削除に失敗しました');
        }
      }
    });
  };

  const handleSelectAllSearchResults = () => {
    setSelectedRecordIds(searchableRecords.map((record) => record.id));
  };

  const handleRecordTableChange = (_pagination, _filters, _sorter, extra) => {
    setDisplayedRecordCount(extra?.currentDataSource?.length ?? searchableRecords.length);
  };

  const getRecordTextFilterProps = (dataIndex) => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
      <div style={{ padding: 8, width: 220 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          placeholder="キーワード"
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => confirm()}
          allowClear
          size="small"
          style={{ marginBottom: 8 }}
        />
        <Space>
          <Button type="primary" size="small" onClick={() => confirm()} icon={<SearchOutlined />}>
            検索
          </Button>
          <Button
            size="small"
            onClick={() => {
              clearFilters?.();
              confirm({ closeDropdown: false });
            }}
          >
            リセット
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered) => <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />,
    onFilter: (value, record) =>
      String(record[dataIndex] ?? '').toLowerCase().includes(String(value).toLowerCase())
  });

  const deleteRecordsByIds = async (recordIds) => {
    const uniqueIds = [...new Set(recordIds)];
    const results = await Promise.allSettled(
      uniqueIds.map((recordId) => axios.delete(`${API_BASE}/records/${recordId}`))
    );

    const successIds = [];
    const failedIds = [];
    results.forEach((result, index) => {
      const targetId = uniqueIds[index];
      if (result.status === 'fulfilled') {
        successIds.push(targetId);
      } else {
        failedIds.push(targetId);
        console.error(`記録削除エラー(${targetId}):`, result.reason);
      }
    });

    return { successIds, failedIds };
  };

  const handleDeleteSelectedRecords = () => {
    if (selectedRecordIds.length === 0) {
      message.info('削除する記録を選択してください');
      return;
    }

    Modal.confirm({
      title: `選択した${selectedRecordIds.length}件の記録を削除しますか？`,
      icon: <ExclamationCircleOutlined />,
      content: 'この操作は元に戻せません。',
      okText: '削除',
      okType: 'danger',
      cancelText: 'キャンセル',
      onOk: async () => {
        const targetIds = [...selectedRecordIds];
        const { successIds, failedIds } = await deleteRecordsByIds(targetIds);

        if (successIds.length > 0) {
          message.success(`${successIds.length}件の記録を削除しました`);
          setSelectedRecordIds((prevIds) => prevIds.filter((id) => !successIds.includes(id)));
          await loadRecords();
        }
        if (failedIds.length > 0) {
          message.error(`${failedIds.length}件の削除に失敗しました`);
        }
      }
    });
  };

  const handleRefreshMovieDetails = async (movieId, forceUpdate = false) => {
    try {
      const response = await axios.post(`${API_BASE}/movies/${movieId}/refresh-details`, {
        force_update: forceUpdate
      });
      const count = response.data?.updated_fields?.length || 0;
      message.success(`作品情報を更新しました（${count}項目）`);
      loadMovies();
    } catch (error) {
      console.error('作品情報更新エラー:', error);
      message.error(extractValidationMessage(error, '作品情報の更新に失敗しました'));
    }
  };

  const executeSync = async (payload) => {
    setIsSyncing(true);
    try {
      const response = await axios.post(`${API_BASE}/search/sync`, payload);

      if (response.data.success) {
        message.success(`同期完了: 新規${response.data.added}件、既存${response.data.existing}件`);
        setIsSyncModalVisible(false);
        syncForm.resetFields();
        loadMovies();
        loadRecords();
      } else if (response.data.cancelled) {
        message.warning(response.data.message || 'ログインブラウザが閉じられたため、同期をキャンセルしました');
      } else if (response.data.can_fallback_to_interactive) {
        Modal.confirm({
          title: '保存済み資格情報でのログインに失敗しました',
          content: '対話ログインに切り替えて同期を続行しますか？',
          okText: '対話ログインへ切替',
          cancelText: 'キャンセル',
          onOk: async () => {
            await executeSync({
              email: null,
              password: null,
              save_credentials: false,
              use_saved_credentials: false
            });
          }
        });
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

  const handleSync = async () => {
    const values = syncForm.getFieldsValue();
    const email = values.email?.trim() || null;
    const password = values.password || null;
    const saveCredentials = Boolean(values.save_credentials);
    const useSavedCredentials = values.use_saved_credentials !== false;

    if ((email && !password) || (!email && password)) {
      message.warning('メールアドレスとパスワードは両方入力してください');
      return;
    }
    if (saveCredentials && (!email || !password)) {
      message.warning('資格情報を保存する場合はメールアドレスとパスワードを入力してください');
      return;
    }

    await executeSync({
      email,
      password,
      save_credentials: saveCredentials,
      use_saved_credentials: useSavedCredentials
    });
  };

  const handleDeleteSavedCredential = () => {
    Modal.confirm({
      title: '保存済み資格情報を削除しますか？',
      icon: <ExclamationCircleOutlined />,
      content: '削除後は自動ログインされません。',
      okText: '削除',
      okType: 'danger',
      cancelText: 'キャンセル',
      onOk: async () => {
        try {
          await axios.delete(`${API_BASE}/credentials/eiga`);
          message.success('保存済み資格情報を削除しました');
          setSavedCredential({ has_credentials: false });
        } catch (error) {
          console.error('資格情報削除エラー:', error);
          message.error('資格情報の削除に失敗しました');
        }
      }
    });
  };

  const selectedRecordCount = selectedRecordIds.length;
  const viewingMethodFilterOptions = useMemo(() => {
    const values = [...new Set(records.map((record) => record.viewing_method).filter(Boolean))];
    return values.map((value) => ({ text: VIEWING_METHOD_LABELS[value] || value, value }));
  }, [records]);
  const moodFilterOptions = useMemo(() => {
    const values = [...new Set(records.map((record) => record.mood).filter(Boolean))];
    return values.map((value) => ({ text: MOOD_LABELS[value] || value, value }));
  }, [records]);

  const recordColumns = [
    {
      title: '映画タイトル',
      dataIndex: 'movie_title',
      key: 'movie_title',
      width: 240,
      sorter: (a, b) => a.movie_title.localeCompare(b.movie_title, 'ja'),
      ...getRecordTextFilterProps('movie_title')
    },
    {
      title: '公開年',
      dataIndex: 'released_year',
      key: 'released_year',
      width: 110,
      sorter: (a, b) => (a.released_year ?? 0) - (b.released_year ?? 0),
      render: (value) => value ?? '-'
    },
    {
      title: '監督',
      dataIndex: 'director',
      key: 'director',
      width: 180,
      sorter: (a, b) => a.director.localeCompare(b.director, 'ja'),
      render: (value) => value || '-',
      ...getRecordTextFilterProps('director')
    },
    {
      title: '視聴日',
      dataIndex: 'viewed_date',
      key: 'viewed_date',
      width: 130,
      defaultSortOrder: 'descend',
      sorter: (a, b) => new Date(a.viewed_date).getTime() - new Date(b.viewed_date).getTime(),
      render: (value) => new Date(value).toLocaleDateString('ja-JP')
    },
    {
      title: '視聴方法',
      dataIndex: 'viewing_method',
      key: 'viewing_method',
      width: 150,
      filters: viewingMethodFilterOptions,
      onFilter: (value, record) => record.viewing_method === value,
      sorter: (a, b) => a.viewing_method_label.localeCompare(b.viewing_method_label, 'ja'),
      render: (_value, record) => <Tag color="blue">{record.viewing_method_label}</Tag>
    },
    {
      title: '評価',
      dataIndex: 'rating',
      key: 'rating',
      width: 160,
      sorter: (a, b) => (a.rating ?? -1) - (b.rating ?? -1),
      render: (value) => (value !== null && value !== undefined ? <Rate allowHalf disabled value={value} /> : '-')
    },
    {
      title: '気分',
      dataIndex: 'mood',
      key: 'mood',
      width: 140,
      filters: moodFilterOptions,
      onFilter: (value, record) => record.mood === value,
      sorter: (a, b) => a.mood_label.localeCompare(b.mood_label, 'ja'),
      render: (_value, record) => (record.mood ? <Tag>{record.mood_label}</Tag> : '-')
    },
    {
      title: '操作',
      key: 'actions',
      width: 310,
      render: (_value, record) => (
        <Space>
          <Button size="small" onClick={() => handleRefreshMovieDetails(record.movie_id, false)}>
            作品情報取得
          </Button>
          <Button size="small" onClick={() => handleRefreshMovieDetails(record.movie_id, true)}>
            強制更新
          </Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditRecordModal(record)}>
            編集
          </Button>
          <Button danger size="small" icon={<DeleteOutlined />} onClick={() => handleDeleteRecord(record.id)}>
            削除
          </Button>
        </Space>
      )
    }
  ];

  const rowSelection = {
    selectedRowKeys: selectedRecordIds,
    onChange: (selectedRowKeys) => setSelectedRecordIds(selectedRowKeys),
    preserveSelectedRowKeys: true,
    columnWidth: 56
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ margin: 0 }}>🎬 映画視聴管理</h1>
        <Space>
          <Input
            placeholder="作品名で検索"
            value={headerSearchQuery}
            onChange={(e) => setHeaderSearchQuery(e.target.value)}
            onPressEnter={handleHeaderSearch}
            style={{ width: 220 }}
            allowClear
          />
          <Button
            icon={<SearchOutlined />}
            onClick={handleHeaderSearch}
            loading={isSearching}
          >
            検索
          </Button>
          <Button
            type="primary"
            icon={<SyncOutlined />}
            onClick={() => setIsSyncModalVisible(true)}
            loading={isSyncing}
          >
            映画.comから同期
          </Button>
        </Space>
      </Header>
      
      <Layout>
        <Content style={{ padding: '20px' }}>
          <Tabs
            activeKey={activeTabKey}
            onChange={setActiveTabKey}
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
                            {record.rating !== null && record.rating !== undefined && <Rate allowHalf disabled value={record.rating} />}
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
                      onSearch={(value) => executeSearch(value, { switchToSearchTab: false })}
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
                    <div style={{ marginBottom: '12px' }}>
                      <Space wrap>
                        <Input
                          allowClear
                          prefix={<SearchOutlined />}
                          placeholder="一覧内検索（タイトル・監督・コメント・視聴方法・気分）"
                          value={recordQuickSearch}
                          onChange={(e) => setRecordQuickSearch(e.target.value)}
                          style={{ width: 420 }}
                        />
                        <Button onClick={handleSelectAllSearchResults} disabled={searchableRecords.length === 0}>
                          検索結果を全選択
                        </Button>
                        <span>選択中: {selectedRecordCount}件</span>
                        <span>表示中: {displayedRecordCount}件 / 全件: {records.length}件</span>
                        <Button
                          onClick={() => setSelectedRecordIds([])}
                          disabled={selectedRecordCount === 0}
                        >
                          選択解除
                        </Button>
                        <Button
                          danger
                          icon={<DeleteOutlined />}
                          onClick={handleDeleteSelectedRecords}
                          disabled={selectedRecordCount === 0}
                        >
                          選択削除
                        </Button>
                      </Space>
                    </div>
                    <Table
                      rowKey="id"
                      columns={recordColumns}
                      dataSource={searchableRecords}
                      rowSelection={rowSelection}
                      onChange={handleRecordTableChange}
                      pagination={false}
                      scroll={{ x: 1600, y: 540 }}
                      locale={{ emptyText: '条件に一致する記録がありません' }}
                      size="middle"
                    />
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
            <Rate allowHalf />
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

      {/* 記録編集モーダル */}
      <Modal
        title="視聴記録を編集"
        open={isEditRecordModalVisible}
        onCancel={() => {
          setIsEditRecordModalVisible(false);
          setEditingRecord(null);
          recordEditForm.resetFields();
        }}
        onOk={() => recordEditForm.submit()}
      >
        <Form
          form={recordEditForm}
          layout="vertical"
          onFinish={handleUpdateRecord}
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
            <Rate allowHalf />
          </Form.Item>

          <Form.Item label="気分" name="mood">
            <Select placeholder="選択してください" allowClear>
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
        onCancel={() => {
          setIsSyncModalVisible(false);
          syncForm.resetFields();
        }}
        okText="同期開始"
        cancelText="キャンセル"
        onOk={handleSync}
        confirmLoading={isSyncing}
      >
        <Spin spinning={isSyncing} tip="ブラウザを起動中...ログインしてください">
          <Form
            form={syncForm}
            layout="vertical"
            initialValues={{
              use_saved_credentials: true,
              save_credentials: false
            }}
          >
            <Form.Item name="use_saved_credentials" valuePropName="checked">
              <Checkbox>保存済み資格情報を優先して使用する</Checkbox>
            </Form.Item>

            <Form.Item label="メールアドレス（任意）" name="email">
              <Input placeholder="example@mail.com" autoComplete="username" />
            </Form.Item>

            <Form.Item label="パスワード（任意）" name="password">
              <Input.Password placeholder="パスワード" autoComplete="current-password" />
            </Form.Item>

            <Form.Item name="save_credentials" valuePropName="checked">
              <Checkbox>保存して次回自動ログイン</Checkbox>
            </Form.Item>
          </Form>

          <div style={{ marginBottom: '12px' }}>
            <strong>保存済み資格情報:</strong>{' '}
            {isCredentialLoading
              ? '読み込み中...'
              : (savedCredential?.has_credentials
                  ? `${savedCredential.email_masked}（active）`
                  : '未保存')}
            {savedCredential?.has_credentials && (
              <Button
                size="small"
                danger
                style={{ marginLeft: '8px' }}
                onClick={handleDeleteSavedCredential}
              >
                削除
              </Button>
            )}
          </div>

          <div style={{ padding: '20px', backgroundColor: '#f0f5ff', borderRadius: '4px', marginBottom: '20px' }}>
            <h3>🔍 同期手順</h3>
            <ol style={{ marginLeft: '20px' }}>
              <li>「同期開始」ボタンをクリックするとブラウザが起動します</li>
              <li>映画.com のログイン画面が表示されます</li>
              <li>その画面でログイン方法を選んでください（メール、Facebook、Google等）</li>
              <li>認証が完了したら、自動的に視聴履歴が取得されます（完了直前の画面を閉じないでください）</li>
            </ol>
            <p style={{ marginTop: '10px', color: '#999', fontSize: '12px' }}>
              🔐 入力した資格情報は、保存ON時のみ暗号化して保存されます。
            </p>
          </div>
        </Spin>
      </Modal>
    </Layout>
  );
}

export default App;
