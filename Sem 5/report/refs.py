"""Reference list (IEEE style, sorted alphabetically as in the Sem 4 report). cite('key') returns '[n]'."""

REFS = {
    "gpp": ("3GPP", '3GPP, "Numbering, addressing and identification," 3rd Generation Partnership Project, Technical Specification TS 23.003.'),
    "bhushan": ("Bhushan", 'Bhushan et al., "SIM Swap Fraud Detection Using AI ML," in Proc. FICTA 2025, Springer, 2026. [Online]. Available: https://link.springer.com/chapter/10.1007/978-3-032-20121-8_27'),
    "breiman": ("Breiman", 'L. Breiman, "Random Forests," Machine Learning, vol. 45, no. 1, pp. 5-32, 2001.'),
    "buterin": ("Buterin", 'V. Buterin, "A Next-Generation Smart Contract and Decentralized Application Platform" (Ethereum White Paper), 2014.'),
    "chen": ("Chen", 'T. Chen and C. Guestrin, "XGBoost: A Scalable Tree Boosting System," in Proc. 22nd ACM SIGKDD Int. Conf. Knowledge Discovery and Data Mining, 2016, pp. 785-794.'),
    "doshi": ("Doshi-Velez", 'F. Doshi-Velez and B. Kim, "Towards A Rigorous Science of Interpretable Machine Learning," arXiv:1702.08608, 2017.'),
    "gdpr": ("European", 'European Parliament and Council, "Regulation (EU) 2016/679 on the protection of natural persons with regard to the processing of personal data (General Data Protection Regulation)," Official Journal of the European Union, L 119, 2016.'),
    "fbi": ("Federal", 'Federal Bureau of Investigation, Internet Crime Complaint Center, "Criminals Increasing SIM Swap Schemes to Steal Millions of Dollars from US Public," Public Service Announcement I-020822-PSA, Feb. 8, 2022. [Online]. Available: https://www.ic3.gov/PSA/2022/PSA220208'),
    "dpdp": ("Government", 'Government of India, "The Digital Personal Data Protection Act, 2023," Act No. 22 of 2023.'),
    "hmac": ("Krawczyk", 'H. Krawczyk, M. Bellare, and R. Canetti, "HMAC: Keyed-Hashing for Message Authentication," IETF RFC 2104, Feb. 1997.'),
    "lee": ("Lee", 'K. Lee, B. Kaiser, J. Mayer, and A. Narayanan, "An Empirical Study of Wireless Carrier Authentication for SIM Swaps," in Proc. 16th Symp. Usable Privacy and Security (SOUPS), 2020, pp. 61-79.'),
    "liu": ("Liu", 'F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation Forest," in Proc. 8th IEEE Int. Conf. Data Mining (ICDM), 2008, pp. 413-422.'),
    "lundberg20": ("Lundberg", 'S. M. Lundberg et al., "From local explanations to global understanding with explainable AI for trees," Nature Machine Intelligence, vol. 2, no. 1, pp. 56-67, 2020.'),
    "lundberg17": ("Lundberg2", 'S. M. Lundberg and S.-I. Lee, "A Unified Approach to Interpreting Model Predictions," in Advances in Neural Information Processing Systems 30 (NeurIPS), 2017, pp. 4765-4774.'),
    "nakamoto": ("Nakamoto", 'S. Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System," 2008. [Online]. Available: https://bitcoin.org/bitcoin.pdf'),
    "fips": ("National", 'National Institute of Standards and Technology, "Secure Hash Standard (SHS)," FIPS PUB 180-4, Aug. 2015.'),
    "fastapi": ("Ramirez", 'S. Ramirez, "FastAPI," web framework documentation. [Online]. Available: https://fastapi.tiangolo.com'),
    "saito": ("Saito", 'T. Saito and M. Rehmsmeier, "The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets," PLOS ONE, vol. 10, no. 3, e0118432, 2015.'),
    "sensors": ("Sensors", '"A Machine Learning and Blockchain Based Efficient Fraud Detection Mechanism," Sensors, vol. 22, no. 19, art. 7162, 2022. [Online]. Available: https://www.mdpi.com/1424-8220/22/19/7162'),
    "shapley": ("Shapley", 'L. S. Shapley, "A value for n-person games," in Contributions to the Theory of Games, vol. II, H. W. Kuhn and A. W. Tucker, Eds. Princeton, NJ, USA: Princeton Univ. Press, 1953, pp. 307-317.'),
    "sim800": ("SIMCom", 'SIMCom Wireless Solutions, "SIM800 Series AT Command Manual."'),
    "solidity": ("Solidity", 'Ethereum Foundation, "Solidity Documentation," version 0.8.24. [Online]. Available: https://docs.soliditylang.org'),
    "sotonye": ("Sotonye", 'I. T. Sotonye, N. Eyidia, and W. N. Abidde, "Combating SIM Swap Fraud in Telecommunications: A Machine Learning Approach and Multi-Factor Authentication as a Preventive Strategy," Journal of Advancement in Communication System, vol. 8, no. 2, pp. 22-27, 2025, doi: 10.5281/zenodo.15591954.'),
    "ganache": ("Truffle", 'Truffle Suite, "Ganache: a personal blockchain for Ethereum development," version 7.9.2.'),
    "wood": ("Wood", 'G. Wood, "Ethereum: A Secure Decentralised Generalised Transaction Ledger," Ethereum Project Yellow Paper, 2014.'),
}

ORDER = sorted(REFS, key=lambda k: REFS[k][0].lower())
NUM = {k: i + 1 for i, k in enumerate(ORDER)}


def cite(*keys):
    return "[" + ", ".join(str(NUM[k]) for k in keys) + "]"


def entries():
    return [(NUM[k], REFS[k][1]) for k in ORDER]
