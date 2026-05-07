import React, { useState, useEffect, useRef } from 'react';
import { Layout, Menu, Typography, theme, Upload, Button, message, Table, Tag, Space, Input, Popconfirm, Modal, Select, Divider, Checkbox } from 'antd';
import {
  UploadOutlined,
  DatabaseOutlined,
  HistoryOutlined,
  InboxOutlined,
  ReloadOutlined,
  EyeOutlined,
  SaveOutlined,
  CheckCircleOutlined,
  SearchOutlined,
  DownloadOutlined,
  PlusOutlined,
  WarningOutlined,
  DeleteOutlined,
  SettingOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;
const { Dragger } = Upload;
const { Option } = Select;

// === СПИСКИ КОЛОНОК ===
const FUNDAMENTAL_COLUMNS = [
  "type", "tag_number", "material_number", "description", "model_number",
  "serial_number", "quantity", "unit", "manufacturer", "part_number",
  "dummy_number", "file_name", "eq_file_name", "price", "leadtime",
  "currency", "source", "operator", "stock_level", "approved"
];

const ADDITIONAL_COLUMNS = [
  "vendor_dwg", "operating_spare_parts", "total_identical_parts",
  "original_po_part_number", "capital_spare_parts", "commissioning_spare_parts",
  "recommended_by_manufacturer", "contractor_review", "appr_qty_cat1",
  "appr_qty_cat3", "appr_qty_cat4"
];

const App = () => {
  const [selectedKey, setSelectedKey] = useState('1');

  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);

  const [inventoryData, setInventoryData] = useState([]);
  const [loadingInventory, setLoadingInventory] = useState(false);
  const [hasLoadedInventory, setHasLoadedInventory] = useState(false);

  const [docsList, setDocsList] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [hasLoadedDocs, setHasLoadedDocs] = useState(false);

  const [masterLists, setMasterLists] = useState([]);
  const [hasLoadedMasterLists, setHasLoadedMasterLists] = useState(false);
  const [selectedMasterId, setSelectedMasterId] = useState('all');
  const [isMasterModalVisible, setIsMasterModalVisible] = useState(false);
  const [masterFileList, setMasterFileList] = useState([]);
  const [uploadingMaster, setUploadingMaster] = useState(false);

  const [selectedDocName, setSelectedDocName] = useState(null);
  const [docData, setDocData] = useState([]);
  const [loadingDocData, setLoadingDocData] = useState(false);
  const [editingCell, setEditingCell] = useState(null);
  const [savingDoc, setSavingDoc] = useState(false);

  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef(null);

  // === НАСТРОЙКИ ПАРСЕРА ===
  const [isSettingsModalVisible, setIsSettingsModalVisible] = useState(false);

  // Основной стейт, который реально влияет на таблицу и скачивание
  const [visibleColumns, setVisibleColumns] = useState(() => {
    const saved = localStorage.getItem('spil_visible_columns');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return [...FUNDAMENTAL_COLUMNS];
      }
    }
    return [...FUNDAMENTAL_COLUMNS];
  });

  // ВРЕМЕННЫЙ стейт для модалки, чтобы таблица не менялась на лету
  const [tempVisibleColumns, setTempVisibleColumns] = useState([]);

  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken();

  const stickyHeaderStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    position: 'sticky',
    top: -24,
    padding: '24px 24px 16px 24px',
    margin: '-24px -24px 16px -24px',
    background: colorBgContainer,
    zIndex: 100,
    borderBottom: '1px solid #f0f0f0'
  };

  // Открытие модалки (копируем текущие настройки во временные)
  const handleOpenSettings = () => {
    setTempVisibleColumns([...visibleColumns]);
    setIsSettingsModalVisible(true);
  };

  // Сохранение настроек (переносим из временных в основные)
  const handleSaveSettings = () => {
    setVisibleColumns(tempVisibleColumns);
    localStorage.setItem('spil_visible_columns', JSON.stringify(tempVisibleColumns));
    message.success('⚙️ View settings saved!');
    setIsSettingsModalVisible(false);
  };

  // Переключение конкретной галочки
  const handleToggleColumn = (colName) => {
    setTempVisibleColumns(prev =>
      prev.includes(colName)
        ? prev.filter(c => c !== colName)
        : [...prev, colName]
    );
  };

  // Выбрать все фундаментальные столбцы сразу (работает с временным стейтом)
  const handleSelectAllFundamental = () => {
    const currentSelections = new Set(tempVisibleColumns);
    FUNDAMENTAL_COLUMNS.forEach(col => currentSelections.add(col));
    setTempVisibleColumns(Array.from(currentSelections));
  };

  const fetchInventory = async () => {
    setLoadingInventory(true);
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/v1/parser/inventory/');
      setInventoryData(response.data.data || []);
      setHasLoadedInventory(true);
    } catch (error) {
      message.error('❌ Error loading database');
    } finally {
      setLoadingInventory(false);
    }
  };

  const fetchDocs = async () => {
    setLoadingDocs(true);
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/v1/parser/docs/');
      setDocsList(response.data.data || []);
      setHasLoadedDocs(true);
    } catch (error) {
      message.error('❌ Error loading documents history');
    } finally {
      setLoadingDocs(false);
    }
  };

  const fetchMasterLists = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/v1/parser/master-lists/');
      setMasterLists(response.data.data || []);
      setHasLoadedMasterLists(true);
    } catch (error) {
      message.error('❌ Error loading master lists');
    }
  };

  const loadDocData = async (filename, status) => {
    if (status === 'processing') return message.warning(`⏳ File '${filename}' is still processing.`);
    if (status === 'error') return message.error(`❌ Error in file '${filename}'.`);
    if (status === 'uploaded') return message.info(`ℹ️ File '${filename}' is not processed yet. Please run the parser.`);
    if (status === 'missing') return message.error(`❌ This file is missing in the database. Please upload it in the 'Add Data' tab.`);

    setLoadingDocData(true);
    setSelectedDocName(filename);
    setEditingCell(null);
    try {
      const response = await axios.get(`http://127.0.0.1:8000/api/v1/parser/docs/${filename}/data`);
      setDocData(response.data.data || []);
    } catch (error) {
      message.error('❌ Error loading document data');
    } finally {
      setLoadingDocData(false);
    }
  };

  useEffect(() => {
    if ((selectedKey === '2' || selectedKey === '3') && !hasLoadedMasterLists) {
      fetchMasterLists();
    }
    if (selectedKey === '2' && !hasLoadedInventory) {
      fetchInventory();
    }
    if (selectedKey === '3' && !hasLoadedDocs) {
      fetchDocs();
    }
  }, [selectedKey, hasLoadedInventory, hasLoadedDocs, hasLoadedMasterLists]);


  const getDisplayDocs = () => {
    if (selectedMasterId === 'all') return docsList;
    const selectedMaster = masterLists.find(ml => ml.id === selectedMasterId);
    if (!selectedMaster) return docsList;

    const requiredFiles = selectedMaster.items.filter(item => item.process.toLowerCase() === 'yes');
    return requiredFiles.map(req => {
      const found = docsList.find(doc => doc.file_name === req.file_name);
      return found ? found : { file_name: req.file_name, status: 'missing', last_update: '-' };
    });
  };

  const getDisplayInventoryData = () => {
    if (selectedMasterId === 'all') return inventoryData;
    const selectedMaster = masterLists.find(ml => ml.id === selectedMasterId);
    if (!selectedMaster) return inventoryData;

    const requiredFiles = selectedMaster.items
      .filter(item => item.process.toLowerCase() === 'yes')
      .map(item => String(item.file_name).trim());

    return inventoryData.filter(item => {
      const materialKey = Object.keys(item).find(k => k.toLowerCase().replace(/_/g, ' ') === 'file name');
      const equipmentKey = Object.keys(item).find(k => k.toLowerCase().replace(/_/g, ' ') === 'eq file name');

      const matchInMaterial = materialKey && item[materialKey] && requiredFiles.includes(String(item[materialKey]).trim());
      const matchInEquipment = equipmentKey && item[equipmentKey] && requiredFiles.includes(String(item[equipmentKey]).trim());

      return matchInMaterial || matchInEquipment;
    });
  };

  const displayDocs = getDisplayDocs();
  const displayInventoryData = getDisplayInventoryData();


  const handleCellSave = (rowIndex, key, newValue) => {
    const newData = [...docData];
    newData[rowIndex] = { ...newData[rowIndex], [key]: newValue };
    setDocData(newData);
    setEditingCell(null);
  };

  const handleSaveChangesToDB = async () => {
    setSavingDoc(true);
    try {
      await axios.post(`http://127.0.0.1:8000/api/v1/parser/docs/${selectedDocName}/save`, docData);
      message.success('💾 Changes successfully saved to the database!');
      fetchDocs();
    } catch (error) {
      message.error('❌ Error saving changes');
    } finally {
      setSavingDoc(false);
    }
  };

  const handleApproveDoc = async () => {
    setSavingDoc(true);
    try {
      await axios.post(`http://127.0.0.1:8000/api/v1/parser/docs/${selectedDocName}/approve`);
      message.success('✅ Document approved successfully!');
      fetchDocs();
      loadDocData(selectedDocName, 'approved');
      setHasLoadedInventory(false);
    } catch (error) {
      message.error('❌ Error approving document');
    } finally {
      setSavingDoc(false);
    }
  };

  const handleStartParsing = async (fileName) => {
    try {
        message.loading({ content: 'Starting parser...', key: 'parse' });
        await axios.post(`http://127.0.0.1:8000/api/v1/parser/docs/${fileName}/parse`);
        message.success({ content: 'Parser successfully started in the background!', key: 'parse', duration: 2 });
        fetchDocs();
    } catch (error) {
        message.error({ content: 'Error starting parser', key: 'parse', duration: 2 });
    }
  };

  const handleDeleteDoc = async (fileName) => {
    try {
      message.loading({ content: 'Deleting document...', key: 'delete' });
      await axios.delete(`http://127.0.0.1:8000/api/v1/parser/docs/${fileName}`);
      message.success({ content: 'Document and its data deleted successfully!', key: 'delete', duration: 3 });

      fetchDocs();

      if (selectedDocName === fileName) {
        setSelectedDocName(null);
        setDocData([]);
      }

      setHasLoadedInventory(false);
    } catch (error) {
      message.error({ content: `Error deleting document: ${error.response?.data?.detail || error.message}`, key: 'delete', duration: 3 });
    }
  };

  // --- ЛОГИКА СКАЧИВАНИЯ CSV ---
  const handleDownloadCSV = () => {
    const approvedData = displayInventoryData.filter(item => item.approved === true);

    if (approvedData.length === 0) {
      message.warning('⚠️ No approved data available for the selected criteria.');
      return;
    }

    let downloadName = 'approved_inventory.csv';
    if (selectedMasterId !== 'all') {
      const selectedMaster = masterLists.find(ml => ml.id === selectedMasterId);
      if (selectedMaster) {
         const cleanName = selectedMaster.name.replace(/\.[^/.]+$/, "");
         downloadName = `inventory-${cleanName}.csv`;
      }
    }

    const allHeaders = Array.from(new Set(approvedData.flatMap(Object.keys)));
    // ОСТАВЛЯЕМ ТОЛЬКО ТЕ КОЛОНКИ, КОТОРЫЕ СЕЙЧАС ВЫБРАНЫ (из ОСНОВНОГО стейта)
    const visibleHeaders = allHeaders.filter(key => visibleColumns.includes(key));

    const escapeCSV = (val) => {
      if (val === null || val === undefined) return '';
      const strVal = String(val);
      if (strVal.includes(';') || strVal.includes('"') || strVal.includes('\n')) {
        return `"${strVal.replace(/"/g, '""')}"`;
      }
      return strVal;
    };

    const csvRows = [];
    csvRows.push(visibleHeaders.map(escapeCSV).join(';'));

    approvedData.forEach(row => {
      csvRows.push(visibleHeaders.map(header => escapeCSV(row[header])).join(';'));
    });

    const csvString = csvRows.join('\n');
    const blob = new Blob(['\uFEFF' + csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', downloadName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };


  const uploadData = async (endpoint, formData, rename = false) => {
    let url = `http://127.0.0.1:8000/api/v1/parser${endpoint}?rename=${rename}`;
    try {
      const response = await axios.post(url, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (response.data.status === 'conflict') {
        Modal.confirm({
          title: 'Files already exist',
          content: `The following files already exist on the server:\n${response.data.conflicts.join(', ')}\n\nWould you like to save them as new copies?`,
          okText: 'Save as copies',
          cancelText: 'Cancel',
          onOk: () => uploadData(endpoint, formData, true),
          onCancel: () => setUploading(false)
        });
      } else {
        message.success(`✅ Files successfully uploaded`);
        setFileList([]);
        setHasLoadedDocs(false);
        setUploading(false);
      }
    } catch (error) {
      message.error(`❌ Error: ${error.response?.data?.detail || error.message}`);
      setUploading(false);
    }
  };

  const handleUpload = () => {
    if (fileList.length === 0) return message.warning('⚠️ Please select at least one file.');
    setUploading(true);

    const actualFiles = fileList.map(f => f.originFileObj || f);
    const zipFile = actualFiles.find(f => f.name.toLowerCase().endsWith('.zip'));

    if (zipFile) {
      const formData = new FormData();
      formData.append('file', zipFile);
      uploadData('/upload/zip/', formData);
      return;
    }

    const excelFiles = actualFiles.filter(f => f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls'));
    if (excelFiles.length > 0) {
      const formData = new FormData();
      excelFiles.forEach(file => formData.append('files', file));
      uploadData('/upload/bulk/', formData);
    } else {
      message.error("Please select .xlsx, .xls files or a .zip archive");
      setUploading(false);
    }
  };

  const handleUploadMasterList = async () => {
    if (masterFileList.length === 0) return message.warning('⚠️ Please select a file.');
    setUploadingMaster(true);

    const formData = new FormData();
    formData.append('file', masterFileList[0].originFileObj || masterFileList[0]);

    try {
      await axios.post('http://127.0.0.1:8000/api/v1/parser/master-lists/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      message.success('✅ Master list successfully uploaded!');
      setMasterFileList([]);
      setIsMasterModalVisible(false);
      setHasLoadedMasterLists(false);
    } catch (error) {
      message.error(`❌ Error: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploadingMaster(false);
    }
  };

  const handleSearch = (selectedKeys, confirm, dataIndex) => {
    confirm();
    setSearchText(selectedKeys[0]);
    setSearchedColumn(dataIndex);
  };

  const handleReset = (clearFilters) => {
    clearFilters();
    setSearchText('');
  };

  const getColumnSearchProps = (dataIndex) => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          ref={searchInput}
          placeholder={`Search in ${dataIndex}`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleSearch(selectedKeys, confirm, dataIndex)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button type="primary" onClick={() => handleSearch(selectedKeys, confirm, dataIndex)} icon={<SearchOutlined />} size="small" style={{ width: 90 }}>
            Search
          </Button>
          <Button onClick={() => clearFilters && handleReset(clearFilters)} size="small" style={{ width: 90 }}>
            Reset
          </Button>
          <Button type="link" size="small" onClick={() => close()}>
            Close
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) => record[dataIndex] ? record[dataIndex].toString().toLowerCase().includes(value.toLowerCase()) : '',
    onFilterDropdownOpenChange: (visible) => {
      if (visible) {
        setTimeout(() => searchInput.current?.select(), 100);
      }
    },
  });

  const commonSorter = (key) => (a, b) => {
    const valA = a[key] || '';
    const valB = b[key] || '';
    if (!isNaN(valA) && !isNaN(valB) && valA !== '' && valB !== '') {
      return Number(valA) - Number(valB);
    }
    return String(valA).localeCompare(String(valB));
  };

  // ФИЛЬТРАЦИЯ КОЛОНОК ДЛЯ ГЛАВНОЙ БАЗЫ ДАННЫХ (использует ОСНОВНОЙ стейт)
  const allUniqueKeys = Array.from(new Set(inventoryData.flatMap((item) => Object.keys(item))));
  const inventoryColumns = allUniqueKeys
    .filter(key => visibleColumns.includes(key))
    .map((key) => ({
      title: key.replace(/_/g, ' ').toUpperCase(),
      dataIndex: key,
      key: key,
      ...getColumnSearchProps(key),
      sorter: commonSorter(key),
      render: (text) => (text === null || text === undefined || text === '' ? '-' : String(text)),
    }));

  const docsColumns = [
    { title: 'FILE NAME', dataIndex: 'file_name', key: 'file_name' },
    {
      title: 'STATUS',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        let color = 'default';
        let icon = null;

        if (status === 'error') color = 'red';
        if (status === 'missing') {
          color = 'magenta';
          icon = <WarningOutlined />;
        }
        if (status === 'uploaded') color = 'purple';
        if (status === 'processing') color = 'default';
        if (status === 'not approved') color = 'blue';
        if (status === 'approved') color = 'green';

        return <Tag color={color} icon={icon}>{status.toUpperCase()}</Tag>;
      }
    },
    { title: 'LAST UPDATE', dataIndex: 'last_update', key: 'last_update' },
    {
      title: 'ACTION',
      key: 'action',
      render: (_, record) => {
        if (record.status === 'missing') {
           return <span style={{ color: 'red', fontWeight: 'bold' }}>Needs Upload</span>;
        }
        return (
          <Space size="middle">
            <Button icon={<DownloadOutlined />} href={`http://127.0.0.1:8000/api/v1/parser/docs/${record.file_name}/download`} target="_blank">
                Download
            </Button>
            {(record.status === 'uploaded' || record.status === 'error') && (
                <Button type="primary" icon={<ReloadOutlined />} onClick={() => handleStartParsing(record.file_name)}>
                    Parse
                </Button>
            )}
            {record.status !== 'uploaded' && record.status !== 'processing' && (
              <Button icon={<EyeOutlined />} onClick={() => loadDocData(record.file_name, record.status)}>
                  View Data
              </Button>
            )}

            <Popconfirm
              title="Delete Document"
              description="Are you sure you want to delete this file AND all its parsed data?"
              onConfirm={() => handleDeleteDoc(record.file_name)}
              okText="Yes, Delete"
              cancelText="Cancel"
              placement="left"
            >
              <Button danger icon={<DeleteOutlined />}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        )
      },
    },
  ];

  // ФИЛЬТРАЦИЯ КОЛОНОК ДЛЯ ДАННЫХ КОНКРЕТНОГО ДОКУМЕНТА
  const docDataKeys = Array.from(new Set(docData.flatMap((item) => Object.keys(item))));
  const docDataColumns = docDataKeys
    .filter(key => visibleColumns.includes(key))
    .map((key) => ({
      title: key.replace(/_/g, ' ').toUpperCase(),
      dataIndex: key,
      key: key,
      ...getColumnSearchProps(key),
      sorter: commonSorter(key),
      render: (text, record, index) => {
        const isEditing = editingCell?.index === index && editingCell?.key === key;
        if (isEditing) {
          return (
            <Input autoFocus defaultValue={text} onBlur={(e) => handleCellSave(index, key, e.target.value)} onPressEnter={(e) => handleCellSave(index, key, e.target.value)} />
          );
        }
        return (
          <div style={{ minHeight: '24px', cursor: 'pointer', padding: '4px' }} onDoubleClick={() => setEditingCell({ index, key })} title="Double click to edit">
            {text === null || text === undefined || text === '' ? '-' : String(text)}
          </div>
        );
      },
    }));

  const uploadProps = {
    onRemove: (file) => setFileList(prev => prev.filter(item => item.uid !== file.uid)),
    beforeUpload: (file) => {
      setFileList(prev => {
        if (prev.some(item => item.uid === file.uid)) return prev;
        return [...prev, file];
      });
      return false;
    },
    fileList,
    multiple: true,
    accept: ".xlsx, .xls, .zip",
  };

  const uploadMasterProps = {
    onRemove: () => setMasterFileList([]),
    beforeUpload: (file) => { setMasterFileList([file]); return false; },
    fileList: masterFileList,
    maxCount: 1,
    accept: ".xlsx, .xls",
  };

  const MasterListSelector = (
    <Space>
      <span style={{ fontWeight: 'bold' }}>Filter by Master List: </span>
      <Select
        style={{ width: 300 }}
        value={selectedMasterId}
        onChange={setSelectedMasterId}
        dropdownRender={(menu) => (
          <>
            {menu}
            <Divider style={{ margin: '8px 0' }} />
            <Space style={{ padding: '0 8px 4px' }}>
              <Button type="text" icon={<PlusOutlined />} onClick={() => setIsMasterModalVisible(true)}>
                Upload new master list
              </Button>
            </Space>
          </>
        )}
      >
        <Option value="all">
          <span style={{ fontWeight: 'bold', color: '#1677ff' }}>All SPILs</span>
        </Option>

        {[...masterLists]
          .sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at))
          .map(ml => (
          <Option key={ml.id} value={ml.id}>
            {ml.name}
          </Option>
        ))}

      </Select>
    </Space>
  );

  const renderContent = () => {
    switch (selectedKey) {
      case '1':
        return (
          <div style={{ maxWidth: 600, margin: '0 auto', textAlign: 'center' }}>
            <h2>Upload Files or Archives</h2>
            <Dragger {...uploadProps} style={{ padding: '20px', marginBottom: '20px' }}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">Click or drag files to this area</p>
              <p className="ant-upload-hint">Supports single or multiple .xlsx / .xls files, as well as .zip archives.</p>
            </Dragger>
            <Button type="primary" onClick={handleUpload} disabled={fileList.length === 0} loading={uploading} icon={<UploadOutlined />} size="large">
              📤 Upload Files
            </Button>
          </div>
        );
      case '2':
        return (
          <div>
            <div style={stickyHeaderStyle}>
              <Title level={3} style={{ margin: 0 }}>Main Database</Title>
              <Space>
                {MasterListSelector}

                <Button icon={<DownloadOutlined />} onClick={handleDownloadCSV} type="primary" style={{ backgroundColor: '#52c41a' }}>
                  Export CSV
                </Button>
                <Button icon={<ReloadOutlined />} onClick={fetchInventory} loading={loadingInventory}>
                  Refresh
                </Button>
              </Space>
            </div>
            <Table dataSource={displayInventoryData} columns={inventoryColumns} loading={loadingInventory} rowKey={(r, i) => r.id || i} scroll={{ x: 'max-content' }} bordered />
          </div>
        );
      case '3':
        return (
          <div>
            <div style={stickyHeaderStyle}>
              <Title level={3} style={{ margin: 0 }}>Documents History</Title>
              <Space>
                {MasterListSelector}
                <Button icon={<ReloadOutlined />} onClick={fetchDocs} loading={loadingDocs}>Refresh Status</Button>
              </Space>
            </div>

            <Table dataSource={displayDocs} columns={docsColumns} loading={loadingDocs} rowKey="file_name" pagination={{ pageSize: 10 }} />

            {selectedDocName && (
              <div style={{ marginTop: 40, borderTop: '2px solid #f0f0f0', paddingTop: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <Title level={4} style={{ margin: 0 }}>
                    Data for: <span style={{ color: '#1677ff' }}>{selectedDocName}</span>
                  </Title>
                  <Space>
                    <Button type="default" icon={<SaveOutlined />} onClick={handleSaveChangesToDB} loading={savingDoc}>
                      Save Changes
                    </Button>
                    <Popconfirm title="Approve Document" description="Are you sure you want to approve this document?" onConfirm={handleApproveDoc} okText="Yes" cancelText="No">
                      <Button type="primary" style={{ backgroundColor: '#52c41a' }} icon={<CheckCircleOutlined />} loading={savingDoc}>
                        Approve
                      </Button>
                    </Popconfirm>
                  </Space>
                </div>
                <Table dataSource={docData} columns={docDataColumns} loading={loadingDocData} rowKey={(r, i) => r.id || i} scroll={{ x: 'max-content' }} bordered size="small" />
              </div>
            )}
          </div>
        );
      default:
        return <div>Select a section</div>;
    }
  };

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      <Sider collapsible>
        <div style={{ padding: '16px', textAlign: 'center' }}>
          <Title level={4} style={{ color: 'white', margin: 0 }}>SPIL Parser</Title>
        </div>
        <Menu theme="dark" defaultSelectedKeys={['1']} mode="inline" onClick={(e) => setSelectedKey(e.key)}
          items={[
            { key: '1', icon: <UploadOutlined />, label: '1. Add Data' },
            { key: '2', icon: <DatabaseOutlined />, label: '2. Main Database' },
            { key: '3', icon: <HistoryOutlined />, label: '3. Documents History' },
          ]}
        />

        <div style={{ position: 'absolute', bottom: '60px', width: '100%', textAlign: 'center' }}>
           <Button type="text" icon={<SettingOutlined />} onClick={handleOpenSettings} style={{ color: 'rgba(255, 255, 255, 0.65)' }}>
             View Settings
           </Button>
        </div>
      </Sider>
      <Layout style={{ overflowY: 'auto' }}>
        <Content style={{ margin: '16px' }}>
          <div style={{ padding: 24, minHeight: 360, width: '100%', background: colorBgContainer, borderRadius: borderRadiusLG }}>
            {renderContent()}

            <Modal
              title="Upload New Master List"
              open={isMasterModalVisible}
              onCancel={() => { setIsMasterModalVisible(false); setMasterFileList([]); }}
              footer={[
                <Button key="cancel" onClick={() => setIsMasterModalVisible(false)}>Cancel</Button>,
                <Button key="submit" type="primary" loading={uploadingMaster} onClick={handleUploadMasterList} disabled={masterFileList.length === 0}>
                  Upload
                </Button>
              ]}
            >
              <p>Upload an Excel file containing exactly two columns: <b>file_name</b> and <b>Process</b></p>
              <Dragger {...uploadMasterProps} style={{ padding: '20px' }}>
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p className="ant-upload-text">Click or drag master list Excel here</p>
              </Dragger>
            </Modal>

            {/* МОДАЛКА НАСТРОЕК ВИДИМОСТИ */}
            <Modal
              title="👁️ View Settings"
              open={isSettingsModalVisible}
              onCancel={() => setIsSettingsModalVisible(false)} // Просто закрываем без сохранения
              width={700}
              footer={[
                <Button key="cancel" onClick={() => setIsSettingsModalVisible(false)}>Cancel</Button>,
                <Button key="submit" type="primary" onClick={handleSaveSettings}>
                  Save View
                </Button>
              ]}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '10px' }}>

                {/* СЕКЦИЯ: ФУНДАМЕНТ */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <Typography.Text strong style={{ color: '#1677ff', fontSize: '16px' }}>Fundamental Columns</Typography.Text>
                    <Button size="small" onClick={handleSelectAllFundamental}>☑ Select All</Button>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    {FUNDAMENTAL_COLUMNS.map(col => (
                        <Checkbox
                          key={col}
                          checked={tempVisibleColumns.includes(col)}
                          onChange={() => handleToggleColumn(col)}
                        >
                          {col.replace(/_/g, ' ').toUpperCase()}
                        </Checkbox>
                    ))}
                  </div>
                </div>

                <Divider style={{ margin: 0 }} />

                {/* СЕКЦИЯ: ДОП СТОЛБЦЫ */}
                <div>
                  <div style={{ marginBottom: '10px' }}>
                    <Typography.Text strong style={{ color: '#8c8c8c', fontSize: '16px' }}>Additional Columns</Typography.Text>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    {ADDITIONAL_COLUMNS.map(col => (
                        <Checkbox
                          key={col}
                          checked={tempVisibleColumns.includes(col)}
                          onChange={() => handleToggleColumn(col)}
                        >
                          {col.replace(/_/g, ' ').toUpperCase()}
                        </Checkbox>
                    ))}
                  </div>
                </div>

              </div>
            </Modal>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;