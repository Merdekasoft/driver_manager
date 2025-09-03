import os
import subprocess
import apt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QListWidget, QPushButton, QLabel, QMessageBox,
                               QProgressBar, QSplitter, QTextEdit, QComboBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon
import re

class DriverInstallThread(QThread):
    progress_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, package_name, action):
        super().__init__()
        self.package_name = package_name
        self.action = action  # 'install' or 'remove'

    def run(self):
        try:
            if self.action == 'install':
                self.progress_signal.emit(f"Installing {self.package_name}...")
                result = subprocess.run(
                    ['apt-get', 'install', '-y', self.package_name],
                    capture_output=True, text=True, check=True
                )
            else:
                self.progress_signal.emit(f"Removing {self.package_name}...")
                result = subprocess.run(
                    ['apt-get', 'remove', '-y', self.package_name],
                    capture_output=True, text=True, check=True
                )

            # Perbaiki bentuk lampau
            past_tense = {'install': 'installed', 'remove': 'removed'}
            self.finished_signal.emit(True, f"Successfully {past_tense[self.action]} {self.package_name}")

        except subprocess.CalledProcessError as e:
            self.finished_signal.emit(False, f"Error: {e.stderr}")

class DriverManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Driver Manager - Debian Testing")
        self.setGeometry(100, 100, 1000, 700)

        # Kategori otomatis berdasarkan keyword pada nama paket
        self.driver_packages = self.get_driver_packages_by_category()

        self.category_icons = {
            'Graphics': QIcon.fromTheme("video-display"),
            'Network': QIcon.fromTheme("network-wired"),
            'Audio': QIcon.fromTheme("audio-card"),
            'Printing': QIcon.fromTheme("printer"),
            'Storage': QIcon.fromTheme("drive-harddisk"),
            'Other': QIcon.fromTheme("package-x-generic"),
    }

        self.installed_drivers = set()
        self.show_recommended_only = False
        self.init_ui()
        self.load_installed_drivers()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Driver Management Area (langsung, tanpa tab)
        driver_layout = QVBoxLayout()
        driver_widget = QWidget()
        driver_widget.setLayout(driver_layout)

        splitter = QSplitter(Qt.Horizontal)

        # Left side - Driver categories
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        category_label = QLabel("Driver Categories:")
        category_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(category_label)

        self.category_list = QListWidget()
        # Tambahkan kategori beserta icon-nya
        for category in self.driver_packages.keys():
            icon = self.category_icons.get(category, QIcon())
            self.category_list.addItem("")
            item = self.category_list.item(self.category_list.count() - 1)
            item.setText(category)
            item.setIcon(icon)
        self.category_list.currentTextChanged.connect(self.on_category_selected)
        left_layout.addWidget(self.category_list)

        # Combobox filter rekomendasi
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Drivers", "Recommended Only"])
        self.filter_combo.setCurrentIndex(0)
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        left_layout.addWidget(self.filter_combo)

        splitter.addWidget(left_widget)

        # Right side - Driver list and actions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        drivers_label = QLabel("Available Drivers:")
        drivers_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(drivers_label)

        self.driver_list = QListWidget()
        right_layout.addWidget(self.driver_list)

        # Action buttons
        button_layout = QHBoxLayout()
        self.install_btn = QPushButton("Install Driver")
        self.install_btn.setIcon(QIcon.fromTheme("list-add"))  # icon install
        self.install_btn.clicked.connect(self.install_driver)
        self.install_btn.setEnabled(False)

        self.remove_btn = QPushButton("Remove Driver")
        self.remove_btn.setIcon(QIcon.fromTheme("list-remove"))  # icon remove
        self.remove_btn.clicked.connect(self.remove_driver)
        self.remove_btn.setEnabled(False)

        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))  # icon refresh
        self.refresh_btn.clicked.connect(self.refresh_drivers)

        button_layout.addWidget(self.install_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addWidget(self.refresh_btn)
        right_layout.addLayout(button_layout)

        # Progress area
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(150)
        self.status_text.setReadOnly(True)
        right_layout.addWidget(self.status_text)

        splitter.addWidget(right_widget)
        splitter.setSizes([200, 600])

        driver_layout.addWidget(splitter)
        # Tambahkan driver_widget ke main_layout
        main_layout.addWidget(driver_widget)

        # Connect signals
        self.driver_list.currentItemChanged.connect(self.on_driver_selected)

    def get_driver_packages_by_category(self):
        cache = apt.Cache()
        categories = {
            'Graphics': [],
            'Network': [],
            'Audio': [],
            'Printing': [],
            'Storage': [],
            'Other': [],
        }
        for pkg in cache:
            name = pkg.name.lower()
            # Pengelompokan sederhana berdasarkan keyword
            if any(x in name for x in ['nvidia', 'intel', 'radeon', 'graphics', 'video', 'mesa', 'xserver']):
                categories['Graphics'].append(pkg.name)
            elif any(x in name for x in ['network', 'net', 'wifi', 'ethernet', 'iwlwifi', 'realtek']):
                categories['Network'].append(pkg.name)
            elif any(x in name for x in ['audio', 'alsa', 'pulseaudio', 'pipewire', 'sound']):
                categories['Audio'].append(pkg.name)
            elif any(x in name for x in ['printer', 'cups', 'hplip']):
                categories['Printing'].append(pkg.name)
            elif any(x in name for x in ['storage', 'mdadm', 'nvme', 'ata', 'scsi', 'disk']):
                categories['Storage'].append(pkg.name)
            elif 'driver' in name or 'firmware' in name:
                categories['Other'].append(pkg.name)
        # Hapus kategori kosong
        return {k: v for k, v in categories.items() if v}

    def on_category_selected(self, category):
        if category:
            self.driver_list.clear()
            drivers = self.driver_packages[category]
            if getattr(self, 'show_recommended_only', False):
                recommended = set(self.get_recommended_drivers())
                drivers = [d for d in drivers if d in recommended]
            self.driver_list.addItems(drivers)
            self.update_driver_status()
            # Pilih item pertama secara otomatis agar tombol aktif
            if self.driver_list.count() > 0:
                self.driver_list.setCurrentRow(0)

    def on_driver_selected(self, current, previous):
        # current: QListWidgetItem | None
        if current:
            driver = current.text().replace('★ ', '').replace('✓ ', '').replace('○ ', '').split(' ')[0]
            is_installed = driver in self.installed_drivers
            self.install_btn.setEnabled(not is_installed)
            self.remove_btn.setEnabled(is_installed)
        else:
            self.install_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)

    def update_driver_status(self):
        current_row = self.driver_list.currentRow()
        recommended = set(self.get_recommended_drivers())
        for i in range(self.driver_list.count()):
            item = self.driver_list.item(i)
            driver = item.text().replace('✓ ', '').replace('○ ', '').replace('★ ', '').split(' ')[0]
            prefix = ""
            if driver in recommended:
                prefix = "★ "
            if driver in self.installed_drivers:
                item.setText(f"{prefix}✓ {driver} (Installed)")
                item.setForeground(Qt.darkGreen)
            else:
                item.setText(f"{prefix}○ {driver}")
                item.setForeground(Qt.black)
        # Kembalikan pemilihan item
        if self.driver_list.count() > 0 and current_row >= 0:
            self.driver_list.setCurrentRow(current_row)
        elif self.driver_list.count() > 0:
            self.driver_list.setCurrentRow(0)
        # Update status tombol sesuai item terpilih
        self.on_driver_selected(self.driver_list.currentItem(), None)

    def on_filter_changed(self, index):
        self.show_recommended_only = (index == 1)
        # Refresh driver list sesuai kategori terpilih
        current_category = self.category_list.currentItem()
        if current_category:
            self.on_category_selected(current_category.text())

    def load_installed_drivers(self):
        try:
            cache = apt.Cache()
            self.installed_drivers.clear()
            for category in self.driver_packages.values():
                for package in category:
                    if package in cache and cache[package].is_installed:
                        self.installed_drivers.add(package)
            self.update_driver_status()
            # Pastikan status tombol juga diupdate
            self.on_driver_selected(self.driver_list.currentItem(), None)
        except Exception as e:
            self.status_text.append(f"Error loading installed drivers: {str(e)}")

    def install_driver(self):
        driver = self.driver_list.currentItem().text().replace('★ ', '').replace('✓ ', '').replace('○ ', '').split(' ')[0]

        reply = QMessageBox.question(
            self, "Confirm Installation",
            f"Are you sure you want to install {driver}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.install_thread = DriverInstallThread(driver, 'install')
            self.install_thread.progress_signal.connect(self.update_progress)
            self.install_thread.finished_signal.connect(self.installation_finished)
            self.install_thread.start()

            self.progress_bar.setVisible(True)
            self.set_buttons_enabled(False)

    def remove_driver(self):
        current_item = self.driver_list.currentItem()
        if not current_item:
            return
        driver = current_item.text().replace('★ ', '').replace('✓ ', '').replace('○ ', '').split(' ')[0]

        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove {driver}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.remove_thread = DriverInstallThread(driver, 'remove')
            self.remove_thread.progress_signal.connect(self.update_progress)
            self.remove_thread.finished_signal.connect(self._after_remove_driver)
            self.remove_thread.start()

            self.progress_bar.setVisible(True)
            self.set_buttons_enabled(False)

    def _after_remove_driver(self, success, message):
        self.installation_finished(success, message)
        # Jalankan apt-get autoremove --purge agar dependen seperti hplip-data juga ikut dihapus
        if success:
            self.status_text.append("Running apt-get autoremove --purge...")
            try:
                result = subprocess.run(['apt-get', 'autoremove', '--purge', '-y'], capture_output=True, text=True, check=True)
                self.status_text.append(result.stdout)
            except subprocess.CalledProcessError as e:
                self.status_text.append(f"Error during autoremove: {e.stderr}")

    def update_progress(self, message):
        self.status_text.append(message)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

    def installation_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.set_buttons_enabled(True)

        self.status_text.append(message)

        # Selalu refresh daftar driver setelah aksi selesai
        self.load_installed_drivers()

        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

    def refresh_drivers(self):
        self.status_text.append("Refreshing driver list...")
        self.load_installed_drivers()
        self.status_text.append("Driver list refreshed.")
        # Update status tombol setelah refresh
        self.on_driver_selected(self.driver_list.currentItem(), None)

    def set_buttons_enabled(self, enabled):
        self.install_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.category_list.setEnabled(enabled)
        self.driver_list.setEnabled(enabled)
        if hasattr(self, 'filter_combo'):
            self.filter_combo.setEnabled(enabled)
        # Setelah mengaktifkan/menonaktifkan semua tombol, update status install/remove sesuai driver terpilih
        current_item = self.driver_list.currentItem()
        if enabled and current_item:
            driver = current_item.text().replace('★ ', '').replace('✓ ', '').replace('○ ', '').split(' ')[0]
            is_installed = driver in self.installed_drivers
            self.install_btn.setEnabled(not is_installed)
            self.remove_btn.setEnabled(is_installed)
        else:
            self.install_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
        self.on_driver_selected(self.driver_list.currentItem(), None)

    def detect_hardware(self):
        # Deteksi hardware dengan lspci
        try:
            output = subprocess.check_output(['lspci', '-nn'], text=True)
            return output.splitlines()
        except Exception as e:
            self.status_text.append(f"Error detecting hardware: {e}")
            return []

    def get_recommended_drivers(self):
        hardware = self.detect_hardware()
        recommended = set()
        for line in hardware:
            # Contoh sederhana: deteksi VGA/Network/Audio dan rekomendasikan driver
            if "VGA compatible controller" in line or "3D controller" in line:
                if "NVIDIA" in line:
                    recommended.add("nvidia-driver")
                elif "Intel" in line:
                    recommended.add("xserver-xorg-video-intel")
                elif "AMD" in line or "ATI" in line:
                    recommended.add("xserver-xorg-video-amdgpu")
            elif "Ethernet controller" in line or "Network controller" in line:
                if "Realtek" in line:
                    recommended.add("firmware-realtek")
                elif "Intel" in line:
                    recommended.add("firmware-iwlwifi")
            elif "Audio device" in line:
                recommended.add("pulseaudio")
                recommended.add("alsa-base")
        return list(recommended)

    # Anda bisa menambahkan tombol "Recommended" untuk menampilkan driver hasil get_recommended_drivers()
    # atau menandai driver yang direkomendasikan di daftar driver_list.