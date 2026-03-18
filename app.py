from httpx import Client
from parsel import Selector
import re
import os

class Konsol:
    @staticmethod
    def log(msg):
        print(msg)
    @staticmethod
    def print(msg):
        print(msg)

konsol = Konsol()

class TRGoals:
    def __init__(self, m3u_dosyasi):
        self.m3u_dosyasi = m3u_dosyasi
        self.httpx = Client(timeout=10, verify=False)
        self.proxy_url_sablonu = "https://nellan-mandalin.hf.space/proxy/m3u?url="

    def referer_domainini_al(self):
        desen = r'#EXTVLCOPT:http-referrer=(https?://[^/]*trgoals[^/]*\.[^\s/]+)'
        with open(self.m3u_dosyasi, "r") as dosya:
            icerik = dosya.read()
        if eslesme := re.search(desen, icerik):
            return eslesme[1]
        raise ValueError("Referer domain bulunamadı!")

    def trgoals_domaini_al(self):
        redirect_url = "https://patronsportv31.cfd/"
        for deneme in range(5):
            if "bit.ly" not in redirect_url:
                break
            try:
                redirect_url = self.redirect_gec(redirect_url)
            except Exception as e:
                konsol.log(f"[red][!] redirect_gec hata: {e}")
                break

        if "bit.ly" in redirect_url or "error" in redirect_url:
            konsol.log("[yellow][!] Bit.ly çözülemedi, yedek linke geçiliyor...")
            try:
                redirect_url = self.redirect_gec("https://t.co/aOAO1eIsqE")
            except Exception as e:
                raise ValueError(f"Yedek link hata verdi: {e}")

        return redirect_url

    def redirect_gec(self, redirect_url: str):
        konsol.log(f"[cyan][~] redirect_gec çağrıldı: {redirect_url}")
        try:
            response = self.httpx.get(redirect_url, follow_redirects=True)
        except Exception as e:
            raise ValueError(f"Redirect hatası: {e}")
        url_zinciri = [str(r.url) for r in response.history] + [str(response.url)]
        for url in reversed(url_zinciri):
            if "trgoals" in url:
                return url.strip("/")
        raise ValueError("'trgoals' içeren link bulunamadı!")

    def yeni_domaini_al(self, eldeki_domain: str) -> str:
        def check(domain):
            if domain == "https://patronsportv31.cfd/":
                raise ValueError("Yeni domain geçersiz")
            return domain

        try:
            return check(self.redirect_gec(eldeki_domain))
        except:
            konsol.log("[red][!] redirect_gec(eldeki_domain) başarısız")
            try:
                return check(self.trgoals_domaini_al())
            except:
                konsol.log("[red][!] trgoals_domaini_al başarısız")
                try:
                    return check(self.redirect_gec("https://t.co/MTLoNVkGQN"))
                except:
                    konsol.log("[red][!] yedek link de başarısız")
                    rakam = int(eldeki_domain.split("trgoals")[1].split(".")[0]) + 1
                    return f"https://trgoals{rakam}.xyz"

    def m3u8_linklerini_proxy_yap(self, icerik: str) -> str:
        konsol.log("[cyan][~] Proxy uygulanıyor...")
        desen = r"(https?://[^\s\"']+?\.m3u8[^\s\"']*)"
        def degistir(eslesme):
            url = eslesme.group(1)
            if not url.startswith(self.proxy_url_sablonu):
                yeni = f"{self.proxy_url_sablonu}{url}"
                konsol.log(f"[yellow]  Değiştirildi: {url} -> {yeni}")
                return yeni
            konsol.log(f"[blue]  Zaten proxy'li: {url}")
            return url
        return re.sub(desen, degistir, icerik)

    def m3u_guncelle(self):
        eldeki = self.referer_domainini_al()
        konsol.log(f"[yellow][~] Bilinen Domain : {eldeki}")

        yeni = self.yeni_domaini_al(eldeki)
        konsol.log(f"[green][+] Yeni Domain : {yeni}")

        kontrol_url = f"{yeni}/channel.html?id=yayin1"

        with open(self.m3u_dosyasi, "r") as dosya:
            icerik = dosya.read()

        if not (eski := re.search(r'https?:\/\/[^\/]+\.(workers\.dev|shop|click|lat)\/?', icerik)):
            raise ValueError("Eski yayın URL'si bulunamadı!")

        eski_url = eski[0]
        konsol.log(f"[yellow][~] Eski Yayın URL : {eski_url}")

        response = self.httpx.get(kontrol_url, follow_redirects=True)
        secici = Selector(response.text)
        baslik = secici.xpath("//title/text()").get()

        if response.status_code != 200 or baslik in ["404 Not Found", "502: Bad gateway"]:
            konsol.log(f"[red][!] Sunucu durumu {response.status_code} — fallback uygulanıyor")
            yayin_url = eski_url
            yeni = eldeki
        else:
            if not (yayin := re.search(r'(?:var|let|const)\s+baseurl\s*=\s*"(https?://[^"]+)"', response.text)):
                konsol.print(response.text)
                raise ValueError("Base URL bulunamadı!")
            yayin_url = yayin[1]

        konsol.log(f"[green][+] Yeni Yayın URL : {yayin_url}")

        yeni_icerik = (
            icerik.replace(eski_url, yayin_url)
                  .replace(eldeki, yeni)
        )
        yeni_icerik = self.m3u8_linklerini_proxy_yap(yeni_icerik)

        with open(self.m3u_dosyasi, "w") as dosya:
            dosya.write(yeni_icerik)

if __name__ == "__main__":
    if not os.path.exists("trgoals.m3u"):
        with open("trgoals.m3u", "w") as f:
            f.write("""#EXTM3U
#EXTVLCOPT:http-referrer=https://trgoals1352.xyz
#EXTINF:-1 group-title="TRGoals Spor",TRGoals HD
https://0ch.d72577a9dd0ec41.sbs/
#EXTINF:-1 group-title="TRGoals Futbol",Maç 1
https://cdn.example.com/live/match1.m3u8
#EXTINF:-1 group-title="TRGoals Basketbol",Maç 2
https://cdn.example.com/live/match2.m3u8
""")
    guncelleyici = TRGoals("trgoals.m3u")
    guncelleyici.m3u_guncelle()
