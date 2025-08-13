from datetime import datetime
import pytz

def format_tanggal_indo(tanggal_str):
    """Format date to Indonesian format"""
    bulan_indo = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    hari_indo = [
        "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"
    ]
    try:
        dt = datetime.strptime(tanggal_str, "%Y-%m-%d")
        hari = hari_indo[dt.weekday()]
        bulan = bulan_indo[dt.month]
        return f"{hari}, {dt.day} {bulan} {dt.year}"
    except Exception:
        return tanggal_str

def parse_tanggal_indo(tanggal_str):
    """Parse Indonesian date format to datetime object"""
    bulan_map = {
        'Januari': 1, 'Februari': 2, 'Maret': 3, 'April': 4, 'Mei': 5, 'Juni': 6,
        'Juli': 7, 'Agustus': 8, 'September': 9, 'Oktober': 10, 'November': 11, 'Desember': 12
    }
    try:
        parts = tanggal_str.split(',')
        if len(parts) == 2:
            _, tgl_bulan_tahun = parts
            tgl_bulan_tahun = tgl_bulan_tahun.strip()
            tgl_split = tgl_bulan_tahun.split(' ')
            if len(tgl_split) == 3:
                hari_num = int(tgl_split[0])
                bulan_num = bulan_map.get(tgl_split[1], 1)
                tahun_num = int(tgl_split[2])
                return datetime(tahun_num, bulan_num, hari_num)
        return datetime.strptime(tanggal_str, '%Y-%m-%d')
    except Exception:
        return None

def get_month_worksheet_name(year, month):
    """Generate worksheet name for specific month"""
    bulan_indo = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    return f"{bulan_indo[month]} {year}"

def get_jakarta_now():
    """Get current datetime in Asia/Jakarta timezone"""
    jakarta = pytz.timezone('Asia/Jakarta')
    return datetime.now(jakarta)
