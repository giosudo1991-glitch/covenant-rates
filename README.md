# კურსი.ge — ვალუტის კურსების აგრეგატორი

საქართველოს ყველა ბანკისა და გამცვლელის ვალუტის კურსი ერთ სივრცეში.

## წყაროები
**ბანკები:** NBG, TBC, BOG, Liberty, ProCredit, Credo, BasisBank, VTB, Space  
**გამცვლელები:** TBC Pay, Rico, Valuto, ლაზიკა, კაპიტალი, MBS

---

## GitHub-ზე ატვირთვა (ნაბიჯ-ნაბიჯ)

### 1. GitHub-ზე ახალი Repository შექმნა
1. გადადი **github.com** → შედი ექაუნთში
2. დააჭირე **"New"** (მწვანე ღილაკი)
3. Repository name: `kursi-ge`
4. Public აირჩიე
5. დააჭირე **"Create repository"**

### 2. ფაილების ატვირთვა
1. Repository-ში დააჭირე **"uploading an existing file"**
2. გადაათრიე ყველა ფაილი (app.py, requirements.txt, render.yaml, static/ საქაღალდე)
3. დააჭირე **"Commit changes"**

---

## Render.com-ზე გაშვება

1. გადადი **render.com** → შედი GitHub ექაუნთით
2. დააჭირე **"New +"** → **"Web Service"**
3. აირჩიე `kursi-ge` repository
4. პარამეტრები:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. დააჭირე **"Create Web Service"**
6. 2-3 წუთში შენი აპი იქნება: `https://kursi-ge.onrender.com`

---

## Play Store-ზე ატვირთვა (PWA)

1. გადადი **bubblewrap** ან **pwabuilder.com**
2. შეიყვანე შენი Render URL
3. ჩამოტვირთე APK
4. ატვირთე Google Play Console-ში

---

## ლოკალური გაშვება (Windows)

```
pip install -r requirements.txt
python app.py
```

შემდეგ გახსენი: http://localhost:5000
