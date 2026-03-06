from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import *
import pandas as pd

# recommend similar products based on one product description and category using TF-IDF and cosine similarity
def get_similar_products(product_id, limit=6):
    products = Product.objects.select_related('category')

    texts = []
    ids = []

    for p in products:
        text = f"{p.name} {p.description} {p.category.name}"
        texts.append(text)
        ids.append(p.id)

    if product_id not in ids:
        return Product.objects.none()

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(texts)

    index = ids.index(product_id)

    similarities = cosine_similarity(
        tfidf_matrix[index],
        tfidf_matrix
    ).flatten()

    similar_indexes = similarities.argsort()[::-1]

    similar_indexes = [
        i for i in similar_indexes if ids[i] != product_id
    ][:limit]

    similar_ids = [ids[i] for i in similar_indexes]

    return Product.objects.filter(id__in=similar_ids)

# recommends products based on the search text using TF-IDF and cosine similarity
def get_similar_products_by_text(search_text, limit=6):
    products = Product.objects.all()

    if not products.exists():
        return Product.objects.none()

    corpus = []
    product_ids = []

    for p in products:
        text = f"{p.name} {p.category} {p.description}"
        corpus.append(text)
        product_ids.append(p.id)

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(corpus)

    search_vector = vectorizer.transform([search_text])

    similarity_scores = cosine_similarity(search_vector, tfidf_matrix)[0]

    similar_indices = similarity_scores.argsort()[::-1][:limit]
    similar_ids = [product_ids[i] for i in similar_indices]

    return Product.objects.filter(id__in=similar_ids)

# build a user interest profile based on their search history and viewed products
def get_user_interest_text(user):
    search_texts = SearchHistory.objects.filter(
        user = user
    ).values_list('query', flat=True)

    viewed_products = ProductView.objects.filter(
        user = user
    ).select_related('product')

    product_texts = [
        f"{pv.product.name} {pv.product.description} {pv.product.category.name}"
        for pv in viewed_products
    ]

    return " ".join(search_texts) + " " + " ".join(product_texts)

# personalized product recommendation system based on user search history and viewed products
def recommend_products_for_user(user, limit=5):
    products = Product.objects.all()

    if not products.exists():
        return Product.objects.none()
    
    user_profile = get_user_interest_text(user)

    corpus = []
    product_ids = []

    for p in products:
        text = f"{p.name} {p.description} {p.category.name}"
        corpus.append(text)
        product_ids.append(p.id)

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(corpus)

    user_vector = vectorizer.transform([user_profile])

    similarity_scores = cosine_similarity(user_vector, tfidf_matrix)[0]

    top_indices = similarity_scores.argsort()[::-1][:limit]
    top_ids = [product_ids[i] for i in top_indices]

    return Product.objects.filter(id__in = top_ids)

def get_item_based_recommendations(product_id, limit=6):

    views = ProductView.objects.all()

    if not views.exists():
        return Product.objects.none()

    data = []

    for v in views:
        data.append({
            "user_id": v.user_id,
            "product_id": v.product_id,
            "interaction": 1
        })

    df = pd.DataFrame(data)

    # create user-item matrix
    user_item_matrix = df.pivot_table(
        index="user_id",
        columns="product_id",
        values="interaction",
        fill_value=0
    )

    # transpose → item-user matrix
    item_matrix = user_item_matrix.T

    similarity = cosine_similarity(item_matrix)

    similarity_df = pd.DataFrame(
        similarity,
        index=item_matrix.index,
        columns=item_matrix.index
    )

    if product_id not in similarity_df.index:
        return Product.objects.none()

    similar_items = similarity_df[product_id] \
        .sort_values(ascending=False)[1:limit+1]

    similar_ids = similar_items.index.tolist()

    return Product.objects.filter(id__in=similar_ids)