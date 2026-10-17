// The site as a whole: its name, owner, colours, analytics and support links. Every page reads them from here.

export const SITE = 'Cinemarium';
export const AUTHOR = 'Kiarash Farajzadehahary';
export const SOURCE = 'https://github.com/kiarashfa/Cinemarium';

/** The page ground, also the browser's theme colour and the manifest's. */
export const BG = '#070707';

/** Google Analytics 4. The measurement ID is public by design, and this is the only place it is written. */
export const GA_ID = 'G-VXPMHYQ0XR';

/** The first year of the project: the copyright runs from it to the year of the build. */
export const COPYRIGHT_START_YEAR = 2026;
const year = new Date().getFullYear();
export const COPYRIGHT = `© ${year > COPYRIGHT_START_YEAR ? `${COPYRIGHT_START_YEAR}–${year}` : year} ${AUTHOR}`;

export const SUPPORT = {
  paypal: 'https://www.paypal.com/donate/?hosted_button_id=S3BD5XFBMMWSJ',
  coffee: 'https://www.buymeacoffee.com/kiarashfa',
};
