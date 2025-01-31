// 全局变量
let currentFile = null;

// 文件管理器类
class FileManager {
    constructor() {
        // 初始化DOM元素引用
        this.uploadZone = document.getElementById('uploadZone');
        this.fileInput = document.getElementById('fileUpload');
        this.progressContainer = document.getElementById('uploadProgress');
        this.progressBar = this.progressContainer?.querySelector('.progress-bar div');
        this.progressText = this.progressContainer?.querySelector('.progress-text');
        this.storageProgress = document.getElementById('storageProgress');
        this.viewToggle = document.getElementById('viewToggle');
        this.sortSelect = document.getElementById('sortSelect');
        this.fileSearch = document.getElementById('fileSearch');
        this.modal = document.getElementById('previewModal');
        
        this.initializeEventListeners();
        this.initializeUploadZone();
        this.initializePreviewModal();
    }

    // 初始化事件监听器
    initializeEventListeners() {
        // 文件排序
        if (this.sortSelect) {
            this.sortSelect.addEventListener('change', this.handleSort.bind(this));
        }
        
        // 视图切换
        if (this.viewToggle) {
            this.viewToggle.addEventListener('click', this.toggleView.bind(this));
        }
        
        // 文件搜索
        if (this.fileSearch) {
            this.fileSearch.addEventListener('input', this.handleSearch.bind(this));
        }
        
        // 存储进度条初始化
        if (this.storageProgress) {
            const percent = this.storageProgress.dataset.percent;
            this.storageProgress.style.width = `${percent}%`;
        }
    }

    // 处理文件排序
    handleSort(event) {
        const fileList = document.querySelector('.file-list');
        const files = Array.from(fileList.children);
        
        files.sort((a, b) => {
            switch(event.target.value) {
                case 'name':
                    return a.querySelector('.file-name').textContent
                        .localeCompare(b.querySelector('.file-name').textContent);
                case 'date':
                    return new Date(b.dataset.date) - new Date(a.dataset.date);
                case 'size':
                    return parseInt(b.dataset.size) - parseInt(a.dataset.size);
                default:
                    return 0;
            }
        });
        
        files.forEach(file => fileList.appendChild(file));
    }

    // 切换视图
    toggleView() {
        const fileList = document.querySelector('.file-list');
        fileList.classList.toggle('list-view');
        this.viewToggle.querySelector('i').classList.toggle('fa-th-large');
        this.viewToggle.querySelector('i').classList.toggle('fa-list');
    }

    // 处理文件搜索
    handleSearch(event) {
        const searchTerm = event.target.value.toLowerCase();
        const files = document.querySelectorAll('.file-item');
        
        files.forEach(file => {
            const fileName = file.querySelector('.file-name').textContent.toLowerCase();
            file.style.display = fileName.includes(searchTerm) ? '' : 'none';
        });
    }

    // 初始化上传区域
    initializeUploadZone() {
        if (!this.uploadZone || !this.fileInput) return;

        this.uploadZone.addEventListener('click', (e) => {
            if (e.target !== this.fileInput) {
                this.fileInput.click();
            }
        });

        this.fileInput.addEventListener('change', () => {
            if (this.fileInput.files.length > 0) {
                this.handleFileUpload(this.fileInput.files[0]);
            }
        });

        this.initializeDragAndDrop();
    }

    // 初始化拖放功能
    initializeDragAndDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, this.preventDefaults);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, () => {
                this.uploadZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.uploadZone.addEventListener(eventName, () => {
                this.uploadZone.classList.remove('dragover');
            });
        });

        this.uploadZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });
    }

    // 处理文件上传
    async handleFileUpload(file) {
        try {
            if (!this.validateFile(file)) return;

            const formData = new FormData();
            formData.append('file', file);

            this.showProgress();
            const response = await this.uploadFile(formData);

            if (response.status === 'success') {
                this.updateProgress(100);
                setTimeout(() => location.reload(), 500);
            } else {
                throw new Error(response.message || '上传失败');
            }
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.resetUpload();
        }
    }

    // 验证文件
    validateFile(file) {
        if (file.size > window.maxUploadSize) {
            this.showError(`文件大小超过限制 (最大 ${window.maxUploadSize/1024/1024}MB)`);
            return false;
        }

        const ext = file.name.split('.').pop().toLowerCase();
        let validType = false;
        
        for (const type in window.allowedFileTypes) {
            if (window.allowedFileTypes[type].includes(ext)) {
                validType = true;
                break;
            }
        }

        if (!validType) {
            this.showError('不支持的文件类型');
            return false;
        }

        return true;
    }

    // 上传文件
    async uploadFile(formData) {
        const response = await fetch('/files/upload/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        });
        return await response.json();
    }

    // 显示进度
    showProgress() {
        if (this.progressContainer) {
            this.progressContainer.style.display = 'block';
        }
    }

    // 更新进度
    updateProgress(percent) {
        if (this.progressBar && this.progressText) {
            this.progressBar.style.width = `${percent}%`;
            this.progressText.textContent = `${percent}%`;
        }
    }

    // 重置上传
    resetUpload() {
        if (this.progressContainer) {
            this.progressContainer.style.display = 'none';
        }
        if (this.fileInput) {
            this.fileInput.value = '';
        }
    }

    // 显示错误
    showError(message) {
        alert(message);
    }

    // 阻止默认行为
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // 初始化预览模态框
    initializePreviewModal() {
        if (!this.modal) return;

        const closeBtn = this.modal.querySelector('.close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.modal.style.display = 'none';
            });
        }

        window.addEventListener('click', (event) => {
            if (event.target === this.modal) {
                this.modal.style.display = 'none';
            }
        });
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    window.fileManager = new FileManager();
}); 